from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from source_models import (
    ALLOWED_CATEGORIES,
    ALLOWED_LEVELS,
    SourceDataError,
    SourceDefinition,
)


class SourceRegistry:
    def __init__(self, registry_path: Path) -> None:
        self.registry_path = registry_path.resolve()
        self._sources = self._load_sources()

    def _load_sources(self) -> tuple[SourceDefinition, ...]:
        try:
            raw_data: Any = json.loads(
                self.registry_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as exc:
            raise SourceDataError(
                "Source Registry를 읽지 못했습니다.\n"
                f"파일: {self.registry_path}\n"
                f"원인: {exc}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise SourceDataError("Source Registry 최상위 값은 객체여야 합니다.")

        raw_sources = raw_data.get("sources")

        if not isinstance(raw_sources, list) or not raw_sources:
            raise SourceDataError("Source Registry에 sources 배열이 없습니다.")

        sources = tuple(SourceDefinition.from_dict(item) for item in raw_sources)
        ids = [source.id for source in sources]

        if len(ids) != len(set(ids)):
            raise SourceDataError("Source Registry에 중복된 source.id가 있습니다.")

        return sources

    @property
    def sources(self) -> tuple[SourceDefinition, ...]:
        return self._sources

    def select(
        self,
        *,
        level: str,
        categories: set[str],
    ) -> tuple[SourceDefinition, ...]:
        normalized_level = level.strip().lower()

        if normalized_level not in ALLOWED_LEVELS:
            raise SourceDataError(
                "지원하지 않는 level입니다: "
                f"{normalized_level}. 지원값: {', '.join(sorted(ALLOWED_LEVELS))}"
            )

        invalid_categories = categories - ALLOWED_CATEGORIES

        if invalid_categories:
            raise SourceDataError(
                "지원하지 않는 category입니다: "
                + ", ".join(sorted(invalid_categories))
            )

        selected = [
            source
            for source in self._sources
            if source.enabled
            and normalized_level in source.levels
            and bool(categories.intersection(source.categories))
        ]

        selected.sort(key=lambda item: (-item.priority, item.id))
        return tuple(selected)
