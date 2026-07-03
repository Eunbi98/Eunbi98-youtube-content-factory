from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


Category = Literal[
    "우주",
    "과학",
    "동물",
    "기술",
    "역사",
    "미스터리",
    "세계뉴스",
    "자연",
    "경제",
    "문화",
]

Emotion = Literal[
    "호기심",
    "충격",
    "미스터리",
    "감동",
    "긴장감",
    "경이로움",
]


@dataclass(frozen=True)
class NewsInput:
    title: str
    summary: str
    source: str = ""
    url: str = ""

    def combined_text(self) -> str:
        return f"{self.title}\n{self.summary}".strip()


@dataclass(frozen=True)
class StorySection:
    section: str
    purpose: str
    target_seconds: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass(frozen=True)
class StoryEngineResult:
    category: Category
    emotion: Emotion
    hook: str
    story_structure: list[StorySection]
    ending: str
    source: str = ""
    url: str = ""
    estimated_duration_sec: int = 52

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["story_structure"] = [
            section.to_dict() for section in self.story_structure
        ]
        return result
