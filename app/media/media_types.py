from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal


MediaType = Literal[
    "real_video",
    "real_image",
    "official_image",
    "animation",
    "infographic",
    "ai_image",
]

PreferredSource = Literal[
    "NASA",
    "ESA",
    "Wikipedia",
    "Generated",
    "Stock",
]


@dataclass(frozen=True)
class MediaPlanItem:
    scene: int
    narration: str
    media_type: MediaType
    preferred_source: PreferredSource
    source_confidence: int
    reason: str
    search_queries: list[str]
    fallback_media_type: MediaType
    visual_note: str
    copyright_note: str = "공식 공개 자료 우선, 사용 조건 확인 필요"

    def to_dict(self) -> dict[str, object]:
        return asdict(self)
