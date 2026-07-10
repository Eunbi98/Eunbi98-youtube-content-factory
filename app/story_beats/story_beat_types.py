from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class StoryBeats:
    hook: str
    misconception: str
    reveal: str
    explanation: str
    second_reveal: str
    human_moment: str
    ending: str
    next_episode_hook: str
    emotion_curve: list[str] = field(
        default_factory=lambda: [
            "curiosity",
            "surprise",
            "understanding",
            "wonder",
        ]
    )

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class StoryBeatGenerationResult:
    episode_id: str
    output_path: str
