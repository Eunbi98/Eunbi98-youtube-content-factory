from __future__ import annotations

from dataclasses import dataclass


TRUST_SCORE_BY_SOURCE = {
    "NASA": 5,
    "NOAA": 5,
    "ESA": 5,
    "Wikimedia Commons": 4,
    "Pexels": 3,
    "Pixabay": 3,
}

SOURCE_PRIORITY = [
    "NASA",
    "NOAA",
    "Wikimedia Commons",
    "ESA",
    "Pexels",
    "Pixabay",
]

MEDIA_TYPES = ["image", "video"]


@dataclass(frozen=True)
class AssetCandidate:
    title: str
    source: str
    url: str
    license: str
    media_type: str
    keywords: list[str]
    trust_score: int

    def to_dict(self) -> dict[str, object]:
        return {
            "title": self.title,
            "source": self.source,
            "url": self.url,
            "license": self.license,
            "media_type": self.media_type,
            "keywords": self.keywords,
            "trust_score": self.trust_score,
        }
