from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


VisualType = Literal[
    "real_video",
    "real_image",
    "ai_image",
    "animation",
    "infographic",
]

CameraMotion = Literal[
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right",
    "none",
]


@dataclass(frozen=True)
class VisualPlanItem:
    scene: int
    narration: str
    visual_type: VisualType
    reason: str
    search_keywords: list[str]
    image_prompt: str
    camera_motion: CameraMotion
    duration: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
