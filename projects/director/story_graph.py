from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


BeatType = Literal[
    "hook",
    "answer",
    "story",
    "fact",
    "ending",
]

MediaType = Literal[
    "image",
    "video",
    "color",
]


@dataclass(frozen=True)
class StoryMedia:
    type: MediaType
    src: Optional[str] = None
    fit: Literal["cover", "contain"] = "cover"
    position: str = "center center"


@dataclass(frozen=True)
class Beat:
    type: BeatType

    title: str
    narration: str
    subtitle: str

    duration: float

    media: StoryMedia

    keywords: list[str] = field(
        default_factory=list,
    )

    background_color: str = "#111111"


@dataclass(frozen=True)
class Story:
    episode_id: str
    title: str

    beats: list[Beat]

    fps: int = 30
    width: int = 1080
    height: int = 1920

    background_color: str = "#000000"
    title_color: str = "#7CFFB2"
    caption_color: str = "#FFFFFF"
    accent_color: str = "#7CFFB2"

    bgm: Optional[str] = None
    voice: Optional[str] = None


def Hook(
    *,
    title: str,
    narration: str,
    subtitle: str,
    duration: float,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#14202B",
) -> Beat:
    return Beat(
        type="hook",
        title=title,
        narration=narration,
        subtitle=subtitle,
        duration=duration,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def Answer(
    *,
    title: str,
    narration: str,
    subtitle: str,
    duration: float,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#223748",
) -> Beat:
    return Beat(
        type="answer",
        title=title,
        narration=narration,
        subtitle=subtitle,
        duration=duration,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def Narrative(
    *,
    title: str,
    narration: str,
    subtitle: str,
    duration: float,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#314A5D",
) -> Beat:
    return Beat(
        type="story",
        title=title,
        narration=narration,
        subtitle=subtitle,
        duration=duration,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def Fact(
    *,
    title: str,
    narration: str,
    subtitle: str,
    duration: float,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#1C3040",
) -> Beat:
    return Beat(
        type="fact",
        title=title,
        narration=narration,
        subtitle=subtitle,
        duration=duration,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def Ending(
    *,
    title: str,
    narration: str,
    subtitle: str,
    duration: float,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#101820",
) -> Beat:
    return Beat(
        type="ending",
        title=title,
        narration=narration,
        subtitle=subtitle,
        duration=duration,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )