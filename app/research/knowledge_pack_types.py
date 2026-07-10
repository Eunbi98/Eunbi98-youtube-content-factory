from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class KnowledgeSource:
    title: str
    publisher: str
    url: str
    source_type: str
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class KnowledgePack:
    episode_id: str
    main_question: str
    common_misconceptions: list[str]
    verified_facts: list[str]
    surprising_facts: list[str]
    timeline: list[str]
    story_materials: list[str]
    visual_ideas: list[str]
    sources: list[KnowledgeSource]

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["sources"] = [
            source.to_dict()
            for source in self.sources
        ]
        return result


@dataclass(frozen=True)
class KnowledgePackResult:
    episode_id: str
    output_path: Path
    markdown_path: Path
    json_path: Path
    source_count: int
