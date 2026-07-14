from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any


class SourceDataError(ValueError):
    """퀴즈 Source Registry 또는 Fact 데이터가 올바르지 않을 때 발생합니다."""


ALLOWED_LEVELS = {
    "elementary",
    "middle",
    "high",
    "current",
}

ALLOWED_CATEGORIES = {
    "science",
    "history",
    "geography",
    "language",
    "society",
    "culture",
    "environment",
    "economy",
    "technology",
    "health",
    "general",
    "current",
}

ALLOWED_COLLECTION_MODES = {
    "local_json",
}


def clean_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise SourceDataError(f"{field_name}은 문자열이어야 합니다.")

    cleaned = " ".join(value.strip().split())

    if not cleaned:
        raise SourceDataError(f"{field_name}은 비어 있을 수 없습니다.")

    return cleaned


def clean_optional_text(value: Any, field_name: str) -> str | None:
    if value is None:
        return None

    return clean_text(value, field_name)


def validate_iso_date(value: str | None, field_name: str) -> str | None:
    if value is None:
        return None

    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise SourceDataError(
            f"{field_name}은 YYYY-MM-DD 형식이어야 합니다: {value}"
        ) from exc

    return value


def normalize_fact_text(text: str) -> str:
    lowered = text.lower()
    compact = re.sub(r"\s+", "", lowered)
    return re.sub(r"[^0-9a-z가-힣]", "", compact)


def make_fact_hash(fact: str, answer: str) -> str:
    payload = f"{normalize_fact_text(fact)}::{normalize_fact_text(answer)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SourceDefinition:
    id: str
    name: str
    organization: str
    homepage: str
    levels: tuple[str, ...]
    categories: tuple[str, ...]
    language: str
    priority: int
    collection_mode: str
    data_file: str
    enabled: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SourceDefinition":
        if not isinstance(data, dict):
            raise SourceDataError("Source Registry의 각 항목은 객체여야 합니다.")

        source_id = clean_text(data.get("id"), "source.id").lower()
        name = clean_text(data.get("name"), f"{source_id}.name")
        organization = clean_text(
            data.get("organization"),
            f"{source_id}.organization",
        )
        homepage = clean_text(data.get("homepage"), f"{source_id}.homepage")
        language = clean_text(
            data.get("language", "ko"),
            f"{source_id}.language",
        ).lower()
        collection_mode = clean_text(
            data.get("collection_mode", "local_json"),
            f"{source_id}.collection_mode",
        ).lower()
        data_file = clean_text(data.get("data_file"), f"{source_id}.data_file")

        raw_levels = data.get("levels")
        raw_categories = data.get("categories")

        if not isinstance(raw_levels, list) or not raw_levels:
            raise SourceDataError(f"{source_id}.levels는 비어 있지 않은 배열이어야 합니다.")

        if not isinstance(raw_categories, list) or not raw_categories:
            raise SourceDataError(
                f"{source_id}.categories는 비어 있지 않은 배열이어야 합니다."
            )

        levels = tuple(
            clean_text(item, f"{source_id}.levels").lower()
            for item in raw_levels
        )
        categories = tuple(
            clean_text(item, f"{source_id}.categories").lower()
            for item in raw_categories
        )

        invalid_levels = set(levels) - ALLOWED_LEVELS
        invalid_categories = set(categories) - ALLOWED_CATEGORIES

        if invalid_levels:
            raise SourceDataError(
                f"{source_id}: 지원하지 않는 level: {', '.join(sorted(invalid_levels))}"
            )

        if invalid_categories:
            raise SourceDataError(
                f"{source_id}: 지원하지 않는 category: "
                f"{', '.join(sorted(invalid_categories))}"
            )

        if collection_mode not in ALLOWED_COLLECTION_MODES:
            raise SourceDataError(
                f"{source_id}: 지원하지 않는 collection_mode: {collection_mode}"
            )

        priority = data.get("priority", 50)
        enabled = data.get("enabled", True)

        if (
            not isinstance(priority, int)
            or isinstance(priority, bool)
            or not 0 <= priority <= 100
        ):
            raise SourceDataError(f"{source_id}.priority는 0~100 정수여야 합니다.")

        if not isinstance(enabled, bool):
            raise SourceDataError(f"{source_id}.enabled는 boolean이어야 합니다.")

        return cls(
            id=source_id,
            name=name,
            organization=organization,
            homepage=homepage,
            levels=levels,
            categories=categories,
            language=language,
            priority=priority,
            collection_mode=collection_mode,
            data_file=data_file,
            enabled=enabled,
        )


@dataclass(frozen=True)
class FactRecord:
    id: str
    level: str
    category: str
    fact: str
    answer: str
    explanation: str
    source_id: str
    source_name: str
    source_url: str
    published_at: str | None
    verified_at: str
    evergreen: bool
    tags: tuple[str, ...]
    source_priority: int
    quality_score: float
    fact_hash: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        source: SourceDefinition,
    ) -> "FactRecord":
        if not isinstance(data, dict):
            raise SourceDataError(f"{source.id}: Fact 항목은 객체여야 합니다.")

        fact_id = clean_text(data.get("id"), f"{source.id}.fact.id")
        level = clean_text(data.get("level"), f"{fact_id}.level").lower()
        category = clean_text(data.get("category"), f"{fact_id}.category").lower()
        fact = clean_text(data.get("fact"), f"{fact_id}.fact")
        answer = clean_text(data.get("answer"), f"{fact_id}.answer")
        explanation = clean_text(data.get("explanation"), f"{fact_id}.explanation")
        source_url = clean_text(
            data.get("source_url", source.homepage),
            f"{fact_id}.source_url",
        )
        published_at = validate_iso_date(
            clean_optional_text(data.get("published_at"), f"{fact_id}.published_at"),
            f"{fact_id}.published_at",
        )
        verified_at = validate_iso_date(
            clean_text(data.get("verified_at"), f"{fact_id}.verified_at"),
            f"{fact_id}.verified_at",
        )

        if level not in ALLOWED_LEVELS:
            raise SourceDataError(f"{fact_id}: 지원하지 않는 level: {level}")

        if category not in ALLOWED_CATEGORIES:
            raise SourceDataError(f"{fact_id}: 지원하지 않는 category: {category}")

        if level not in source.levels:
            raise SourceDataError(
                f"{fact_id}: level {level}이 Source {source.id} 설정과 일치하지 않습니다."
            )

        if category not in source.categories:
            raise SourceDataError(
                f"{fact_id}: category {category}가 Source {source.id} 설정과 일치하지 않습니다."
            )

        evergreen = data.get("evergreen", level != "current")

        if not isinstance(evergreen, bool):
            raise SourceDataError(f"{fact_id}.evergreen은 boolean이어야 합니다.")

        raw_tags = data.get("tags", [])

        if not isinstance(raw_tags, list):
            raise SourceDataError(f"{fact_id}.tags는 배열이어야 합니다.")

        tags = tuple(
            clean_text(tag, f"{fact_id}.tags").lower()
            for tag in raw_tags
        )

        quality_score = cls.calculate_quality_score(
            source_priority=source.priority,
            fact=fact,
            answer=answer,
            explanation=explanation,
            source_url=source_url,
            verified_at=verified_at,
            evergreen=evergreen,
        )

        return cls(
            id=fact_id,
            level=level,
            category=category,
            fact=fact,
            answer=answer,
            explanation=explanation,
            source_id=source.id,
            source_name=source.name,
            source_url=source_url,
            published_at=published_at,
            verified_at=verified_at,
            evergreen=evergreen,
            tags=tags,
            source_priority=source.priority,
            quality_score=quality_score,
            fact_hash=make_fact_hash(fact, answer),
        )

    @staticmethod
    def calculate_quality_score(
        *,
        source_priority: int,
        fact: str,
        answer: str,
        explanation: str,
        source_url: str,
        verified_at: str,
        evergreen: bool,
    ) -> float:
        score = source_priority * 0.45

        if 12 <= len(fact) <= 120:
            score += 15
        elif len(fact) <= 180:
            score += 8

        if 1 <= len(answer) <= 30:
            score += 12

        if 12 <= len(explanation) <= 160:
            score += 12
        elif len(explanation) <= 220:
            score += 6

        if source_url.startswith("https://"):
            score += 8

        verified_date = date.fromisoformat(verified_at)
        age_days = (date.today() - verified_date).days

        if evergreen:
            score += 8
        elif age_days <= 30:
            score += 8
        elif age_days <= 90:
            score += 4

        return round(min(100.0, score), 2)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["tags"] = list(self.tags)
        return data


@dataclass(frozen=True)
class FactPool:
    version: str
    generated_at: str
    level: str
    categories: tuple[str, ...]
    source_count: int
    fact_count: int
    minimum_quality: float
    facts: tuple[FactRecord, ...]

    @classmethod
    def create(
        cls,
        *,
        level: str,
        categories: set[str],
        source_count: int,
        minimum_quality: float,
        facts: list[FactRecord],
    ) -> "FactPool":
        generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()

        return cls(
            version="1.0",
            generated_at=generated_at,
            level=level,
            categories=tuple(sorted(categories)),
            source_count=source_count,
            fact_count=len(facts),
            minimum_quality=minimum_quality,
            facts=tuple(facts),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "level": self.level,
            "categories": list(self.categories),
            "source_count": self.source_count,
            "fact_count": self.fact_count,
            "minimum_quality": self.minimum_quality,
            "facts": [fact.to_dict() for fact in self.facts],
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(path.suffix + ".tmp")
        temporary_path.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary_path.replace(path)
