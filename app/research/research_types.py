from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class ResearchInput:
    title: str
    summary: str = ""
    source: str = ""
    url: str = ""

    def combined_text(self) -> str:
        return f"{self.title}\n{self.summary}".strip()


@dataclass(frozen=True)
class SourcePlanItem:
    source_type: str
    purpose: str
    query_hint: str
    priority: int = 3

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class ResearchContext:
    topic: str
    core_question: str
    background_points: list[str] = field(default_factory=list)
    related_angles: list[str] = field(default_factory=list)
    story_clues: list[str] = field(default_factory=list)
    possible_resolution: str = ""
    source_plan: list[SourcePlanItem] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["source_plan"] = [
            item.to_dict()
            for item in self.source_plan
        ]
        return result
