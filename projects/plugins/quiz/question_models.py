from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class QuestionDataError(ValueError):
    """Fact Pool 또는 Question Pool 데이터가 올바르지 않을 때 발생합니다."""


def clean_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise QuestionDataError(f"{field_name}은 문자열이어야 합니다.")

    cleaned = " ".join(value.strip().split())

    if not cleaned:
        raise QuestionDataError(f"{field_name}은 비어 있을 수 없습니다.")

    return cleaned


def normalize_text(value: str) -> str:
    compact = re.sub(r"\s+", "", value.lower())
    return re.sub(r"[^0-9a-z가-힣]", "", compact)


def make_question_hash(question: str, answer: str) -> str:
    payload = f"{normalize_text(question)}::{normalize_text(answer)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class QuestionRecord:
    id: str
    fact_id: str
    level: str
    category: str
    question: str
    answer: str
    explanation: str
    question_style: str
    keywords: tuple[str, ...]
    source_id: str
    source_name: str
    source_url: str
    published_at: str | None
    verified_at: str
    evergreen: bool
    fact_quality_score: float
    quality_score: float
    question_hash: str

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["keywords"] = list(self.keywords)
        return data


@dataclass(frozen=True)
class QuestionPool:
    version: str
    generated_at: str
    level: str
    categories: tuple[str, ...]
    question_count: int
    minimum_quality: float
    questions: tuple[QuestionRecord, ...]

    @classmethod
    def create(
        cls,
        *,
        level: str,
        categories: set[str],
        minimum_quality: float,
        questions: list[QuestionRecord],
    ) -> "QuestionPool":
        return cls(
            version="1.0",
            generated_at=datetime.now(timezone.utc)
            .replace(microsecond=0)
            .isoformat(),
            level=level,
            categories=tuple(sorted(categories)),
            question_count=len(questions),
            minimum_quality=minimum_quality,
            questions=tuple(questions),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "level": self.level,
            "categories": list(self.categories),
            "question_count": self.question_count,
            "minimum_quality": self.minimum_quality,
            "questions": [item.to_dict() for item in self.questions],
        }

    def save(self, path: Path) -> None:
        resolved = path.resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        temporary = resolved.with_suffix(resolved.suffix + ".tmp")
        temporary.write_text(
            json.dumps(self.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(resolved)
