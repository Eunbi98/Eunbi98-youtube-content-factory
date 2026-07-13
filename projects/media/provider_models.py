from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


MediaType = Literal["image", "video"]
Orientation = Literal["portrait", "landscape", "square", "unknown"]


@dataclass(frozen=True, slots=True)
class MediaCandidate:
    provider: str
    media_id: str
    title: str
    query: str
    media_type: MediaType
    mime_type: str
    source_url: str
    download_url: str
    thumbnail_url: str | None
    author: str | None
    author_url: str | None
    license_name: str | None
    license_url: str | None
    width: int
    height: int
    orientation: Orientation
    file_extension: str
    description: str | None = None
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def infer_orientation(
    width: int,
    height: int,
) -> Orientation:
    if width <= 0 or height <= 0:
        return "unknown"

    ratio = width / height

    if 0.95 <= ratio <= 1.05:
        return "square"

    if ratio < 1.0:
        return "portrait"

    return "landscape"
