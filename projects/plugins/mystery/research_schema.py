from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


SourceTier = Literal[
    "official",
    "academic",
    "reference",
    "news",
]


@dataclass(frozen=True)
class ResearchQuestion:
    id: str
    category: str
    question: str
    priority: int


@dataclass(frozen=True)
class SourceRecommendation:
    tier: SourceTier
    purpose: str
    query_hint: str


@dataclass(frozen=True)
class ResearchResult:
    topic: str
    normalized_topic: str
    search_keywords: list[str]
    research_questions: list[ResearchQuestion]
    recommended_sources: list[SourceRecommendation]
    story_angles: list[str]
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
