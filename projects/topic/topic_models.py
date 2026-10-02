from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class TopicSourceItem:
    title: str
    url: str
    source: str
    published_at: str | None = None


@dataclass(frozen=True)
class TopicCandidate:
    rank: int
    category: str
    topic: str
    angle: str
    score: float
    reasons: list[str]
    search_queries: list[str]
    source_count: int = 0
    sources: list[TopicSourceItem] = field(default_factory=list)
    production_ready: bool = False
    readiness_score: int = 0
    readiness_checks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TopicFinderResult:
    category: str
    generated_at: str
    mode: str
    candidate_count: int
    candidates: list[TopicCandidate]
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)
