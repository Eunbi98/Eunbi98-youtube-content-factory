from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


EvidenceType = Literal[
    "fact",
    "case",
    "counterpoint",
    "timeline",
    "quote",
]

SourceTier = Literal[
    "official",
    "academic",
    "reference",
    "news",
    "unknown",
]


@dataclass(frozen=True)
class RawEvidence:
    title: str
    claim: str
    source_name: str
    source_url: str
    source_tier: SourceTier = "unknown"
    evidence_type: EvidenceType = "fact"
    published_at: str | None = None
    keywords: list[str] = field(
        default_factory=list,
    )


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    title: str
    claim: str
    source_name: str
    source_url: str
    source_tier: SourceTier
    evidence_type: EvidenceType
    published_at: str | None
    keywords: list[str]

    reliability_score: float
    interest_score: float
    visual_score: float
    total_score: float


@dataclass(frozen=True)
class EvidenceResult:
    topic: str
    items: list[EvidenceItem]
    rejected_count: int
    duplicate_count: int

    def to_dict(self) -> dict:
        return asdict(self)
