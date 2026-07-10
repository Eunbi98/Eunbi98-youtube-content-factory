from __future__ import annotations

from dataclasses import asdict, dataclass, field


@dataclass(frozen=True)
class Beat:
    start_time: int
    end_time: int
    purpose: str
    narration_intent: str
    caption_text: str
    visual_direction: str
    emotion: str
    transition_note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class BeatSheet:
    episode_id: str
    duration_seconds: int
    beats: list[Beat] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        result = asdict(self)
        result["beats"] = [
            beat.to_dict()
            for beat in self.beats
        ]
        return result


@dataclass(frozen=True)
class BeatSheetGenerationResult:
    episode_id: str
    json_path: str
    markdown_path: str
    duration_seconds: int
