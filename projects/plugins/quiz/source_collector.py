from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from source_models import FactPool, FactRecord, SourceDataError, SourceDefinition
from source_registry import SourceRegistry


class SourceCollector:
    def __init__(
        self,
        *,
        registry: SourceRegistry,
        source_data_dir: Path,
    ) -> None:
        self.registry = registry
        self.source_data_dir = source_data_dir.resolve()

    def collect(
        self,
        *,
        level: str,
        categories: set[str],
        minimum_quality: float,
        limit: int,
    ) -> FactPool:
        if not 0 <= minimum_quality <= 100:
            raise SourceDataError("minimum_quality는 0~100 사이여야 합니다.")

        if limit <= 0:
            raise SourceDataError("limit은 1 이상이어야 합니다.")

        sources = self.registry.select(level=level, categories=categories)

        if not sources:
            raise SourceDataError(
                f"level={level}, categories={sorted(categories)} 조건에 맞는 Source가 없습니다."
            )

        collected: list[FactRecord] = []

        for source in sources:
            collected.extend(
                self._load_source_facts(
                    source=source,
                    level=level,
                    categories=categories,
                )
            )

        deduplicated: dict[str, FactRecord] = {}

        for fact in collected:
            current = deduplicated.get(fact.fact_hash)

            if current is None or fact.quality_score > current.quality_score:
                deduplicated[fact.fact_hash] = fact

        filtered = [
            fact
            for fact in deduplicated.values()
            if fact.quality_score >= minimum_quality
        ]

        filtered.sort(
            key=lambda item: (
                -item.quality_score,
                -item.source_priority,
                item.id,
            )
        )

        selected = filtered[:limit]

        if not selected:
            raise SourceDataError(
                "품질 기준을 통과한 Fact가 없습니다. "
                f"minimum_quality={minimum_quality}"
            )

        return FactPool.create(
            level=level,
            categories=categories,
            source_count=len(sources),
            minimum_quality=minimum_quality,
            facts=selected,
        )

    def _load_source_facts(
        self,
        *,
        source: SourceDefinition,
        level: str,
        categories: set[str],
    ) -> list[FactRecord]:
        if source.collection_mode != "local_json":
            raise SourceDataError(
                f"{source.id}: 지원하지 않는 collection_mode: {source.collection_mode}"
            )

        source_path = (self.source_data_dir / source.data_file).resolve()

        try:
            source_path.relative_to(self.source_data_dir)
        except ValueError as exc:
            raise SourceDataError(
                f"{source.id}: data_file이 source_data 폴더 밖을 가리킵니다."
            ) from exc

        try:
            raw_data: Any = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceDataError(
                f"{source.id}: Source Pack을 읽지 못했습니다.\n"
                f"파일: {source_path}\n원인: {exc}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise SourceDataError(f"{source.id}: Source Pack 최상위 값은 객체여야 합니다.")

        raw_facts = raw_data.get("facts")

        if not isinstance(raw_facts, list):
            raise SourceDataError(f"{source.id}: facts 배열이 없습니다.")

        facts: list[FactRecord] = []

        for raw_fact in raw_facts:
            fact = FactRecord.from_dict(raw_fact, source=source)

            if fact.level != level:
                continue

            if fact.category not in categories:
                continue

            facts.append(fact)

        return facts
