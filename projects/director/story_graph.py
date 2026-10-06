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
    """
    Story를 구성하는 의미 단위입니다.

    Beat는 콘텐츠 정보만 보유합니다.
    장면의 duration과 start 같은 시간 정보는 Factory Core에서
    자동으로 계산합니다.
    """

    type: BeatType

    title: str
    narration: str
    subtitle: str

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
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#14202B",
    duration: Optional[float] = None,
) -> Beat:
    """
    Hook Beat를 생성합니다.

    duration은 이전 Story 코드와의 호환을 위해 임시로 허용하지만,
    Beat에 저장하거나 장면 길이 계산에 사용하지 않습니다.
    """

    _ignore_legacy_duration(duration)

    return Beat(
        type="hook",
        title=title,
        narration=narration,
        subtitle=subtitle,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def Answer(
    *,
    title: str,
    narration: str,
    subtitle: str,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#223748",
    duration: Optional[float] = None,
) -> Beat:
    """
    Answer Beat를 생성합니다.

    duration은 이전 Story 코드와의 호환을 위해 임시로 허용하지만,
    Beat에 저장하거나 장면 길이 계산에 사용하지 않습니다.
    """

    _ignore_legacy_duration(duration)

    return Beat(
        type="answer",
        title=title,
        narration=narration,
        subtitle=subtitle,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def Narrative(
    *,
    title: str,
    narration: str,
    subtitle: str,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#314A5D",
    duration: Optional[float] = None,
) -> Beat:
    """
    Story Beat를 생성합니다.

    duration은 이전 Story 코드와의 호환을 위해 임시로 허용하지만,
    Beat에 저장하거나 장면 길이 계산에 사용하지 않습니다.
    """

    _ignore_legacy_duration(duration)

    return Beat(
        type="story",
        title=title,
        narration=narration,
        subtitle=subtitle,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def Fact(
    *,
    title: str,
    narration: str,
    subtitle: str,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#1C3040",
    duration: Optional[float] = None,
) -> Beat:
    """
    Fact Beat를 생성합니다.

    duration은 이전 Story 코드와의 호환을 위해 임시로 허용하지만,
    Beat에 저장하거나 장면 길이 계산에 사용하지 않습니다.
    """

    _ignore_legacy_duration(duration)

    return Beat(
        type="fact",
        title=title,
        narration=narration,
        subtitle=subtitle,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def Ending(
    *,
    title: str,
    narration: str,
    subtitle: str,
    media: StoryMedia,
    keywords: Optional[list[str]] = None,
    background_color: str = "#101820",
    duration: Optional[float] = None,
) -> Beat:
    """
    Ending Beat를 생성합니다.

    duration은 이전 Story 코드와의 호환을 위해 임시로 허용하지만,
    Beat에 저장하거나 장면 길이 계산에 사용하지 않습니다.
    """

    _ignore_legacy_duration(duration)

    return Beat(
        type="ending",
        title=title,
        narration=narration,
        subtitle=subtitle,
        media=media,
        keywords=keywords or [],
        background_color=background_color,
    )


def _ignore_legacy_duration(
    duration: Optional[float],
) -> None:
    """
    Patch 5-3 이전 Story 코드와의 호환을 위한 임시 처리입니다.

    기존 에피소드가 duration 인자를 전달해도 실행은 유지하지만,
    해당 값은 Duration Planner에서 사용하지 않습니다.

    향후 기존 Story 파일에서 duration 인자가 모두 제거되면
    이 인자와 함수도 삭제할 수 있습니다.
    """

    if duration is not None and duration <= 0:
        raise ValueError(
            "Legacy duration을 전달하는 경우 "
            "0보다 큰 값이어야 합니다."
        )