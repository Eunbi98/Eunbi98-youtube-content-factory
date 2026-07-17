from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from story_graph import (
    Answer,
    Beat,
    Ending,
    Fact,
    Hook,
    Narrative,
    Story,
    StoryMedia,
)


class EpisodeSpecError(ValueError):
    """episode.json 형식 또는 값이 올바르지 않을 때 발생합니다."""


BEAT_BUILDERS: dict[str, Callable[..., Beat]] = {
    "hook": Hook,
    "answer": Answer,
    "story": Narrative,
    "fact": Fact,
    "ending": Ending,
}


def load_episode_spec(
    spec_path: Path,
    *,
    expected_episode_id: str | None = None,
) -> Story:
    try:
        raw_data: Any = json.loads(
            spec_path.read_text(encoding="utf-8-sig")
        )
    except OSError as exc:
        raise EpisodeSpecError(
            "episode.json을 읽지 못했습니다. "
            f"파일: {spec_path}\n원인: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise EpisodeSpecError(
            "episode.json의 JSON 형식이 올바르지 않습니다. "
            f"파일: {spec_path}\n"
            f"줄: {exc.lineno}, 열: {exc.colno}\n"
            f"원인: {exc.msg}"
        ) from exc

    if not isinstance(raw_data, dict):
        raise EpisodeSpecError(
            "episode.json 최상위 값은 객체여야 합니다."
        )

    episode_id = _required_text(
        raw_data,
        "episodeId",
        context="episode",
    ).lower()

    if (
        expected_episode_id is not None
        and episode_id != expected_episode_id.lower()
    ):
        raise EpisodeSpecError(
            "episode.json의 episodeId가 요청값과 다릅니다. "
            f"파일: {episode_id}, 요청: {expected_episode_id.lower()}"
        )

    raw_scenes = raw_data.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise EpisodeSpecError(
            "episode.json의 scenes는 비어 있지 않은 배열이어야 합니다."
        )

    beats = [
        _parse_scene(
            raw_scene,
            index=index,
            episode_id=episode_id,
        )
        for index, raw_scene in enumerate(raw_scenes, start=1)
    ]

    if beats[0].type != "hook":
        raise EpisodeSpecError(
            "첫 번째 Scene의 type은 hook이어야 합니다."
        )
    if beats[-1].type != "ending":
        raise EpisodeSpecError(
            "마지막 Scene의 type은 ending이어야 합니다."
        )

    raw_theme = raw_data.get("theme", {})
    if not isinstance(raw_theme, dict):
        raise EpisodeSpecError(
            "episode.json의 theme은 객체여야 합니다."
        )

    return Story(
        episode_id=episode_id,
        title=_required_text(
            raw_data,
            "title",
            context="episode",
        ),
        beats=beats,
        fps=_positive_int(raw_data, "fps", default=30),
        width=_positive_int(raw_data, "width", default=1080),
        height=_positive_int(raw_data, "height", default=1920),
        background_color=_optional_text(
            raw_theme,
            "backgroundColor",
            default="#000000",
        ),
        title_color=_optional_text(
            raw_theme,
            "titleColor",
            default="#7CFFB2",
        ),
        caption_color=_optional_text(
            raw_theme,
            "captionColor",
            default="#FFFFFF",
        ),
        accent_color=_optional_text(
            raw_theme,
            "accentColor",
            default="#7CFFB2",
        ),
        bgm=_nullable_text(raw_data, "bgm"),
        voice=_nullable_text(raw_data, "voice"),
    )


def _parse_scene(
    raw_scene: Any,
    *,
    index: int,
    episode_id: str,
) -> Beat:
    context = f"scenes[{index}]"
    if not isinstance(raw_scene, dict):
        raise EpisodeSpecError(
            f"{context}은 객체여야 합니다."
        )

    beat_type = _required_text(
        raw_scene,
        "type",
        context=context,
    ).lower()
    beat_builder = BEAT_BUILDERS.get(beat_type)
    if beat_builder is None:
        supported = ", ".join(BEAT_BUILDERS)
        raise EpisodeSpecError(
            f"{context}.type이 올바르지 않습니다. "
            f"요청: {beat_type}, 지원: {supported}"
        )

    narration = _required_text(
        raw_scene,
        "narration",
        context=context,
    )

    raw_media = raw_scene.get("media", {})
    if not isinstance(raw_media, dict):
        raise EpisodeSpecError(
            f"{context}.media는 객체여야 합니다."
        )

    media_type = _optional_text(
        raw_media,
        "type",
        default="image",
    ).lower()
    if media_type not in {"image", "video", "color"}:
        raise EpisodeSpecError(
            f"{context}.media.type이 올바르지 않습니다. "
            f"요청: {media_type}, 지원: image, video, color"
        )

    default_src = (
        None
        if media_type == "color"
        else f"{episode_id}/scene_{index:03d}.jpg"
    )
    media_src = _nullable_text(
        raw_media,
        "src",
        default=default_src,
    )

    raw_keywords = raw_scene.get("keywords", [])
    if not isinstance(raw_keywords, list):
        raise EpisodeSpecError(
            f"{context}.keywords는 문자열 배열이어야 합니다."
        )

    keywords: list[str] = []
    for keyword_index, raw_keyword in enumerate(
        raw_keywords,
        start=1,
    ):
        if not isinstance(raw_keyword, str) or not raw_keyword.strip():
            raise EpisodeSpecError(
                f"{context}.keywords[{keyword_index}]는 "
                "비어 있지 않은 문자열이어야 합니다."
            )
        keywords.append(raw_keyword.strip())

    fit = _optional_text(raw_media, "fit", default="cover")
    if fit not in {"cover", "contain"}:
        raise EpisodeSpecError(
            f"{context}.media.fit은 cover 또는 contain이어야 합니다."
        )

    return beat_builder(
        title=_required_text(
            raw_scene,
            "title",
            context=context,
        ),
        narration=narration,
        subtitle=narration,
        media=StoryMedia(
            type=media_type,
            src=media_src,
            fit=fit,
            position=_optional_text(
                raw_media,
                "position",
                default="center center",
            ),
        ),
        keywords=keywords,
        background_color=_optional_text(
            raw_scene,
            "backgroundColor",
            default=_default_background_color(beat_type),
        ),
    )


def _required_text(
    data: dict[str, Any],
    key: str,
    *,
    context: str,
) -> str:
    raw_value = data.get(key)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise EpisodeSpecError(
            f"{context}.{key}는 비어 있지 않은 문자열이어야 합니다."
        )
    return raw_value.strip()


def _optional_text(
    data: dict[str, Any],
    key: str,
    *,
    default: str,
) -> str:
    raw_value = data.get(key, default)
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise EpisodeSpecError(
            f"{key}는 비어 있지 않은 문자열이어야 합니다."
        )
    return raw_value.strip()


def _nullable_text(
    data: dict[str, Any],
    key: str,
    *,
    default: str | None = None,
) -> str | None:
    raw_value = data.get(key, default)
    if raw_value is None:
        return None
    if not isinstance(raw_value, str) or not raw_value.strip():
        raise EpisodeSpecError(
            f"{key}는 null 또는 비어 있지 않은 문자열이어야 합니다."
        )
    return raw_value.strip()


def _positive_int(
    data: dict[str, Any],
    key: str,
    *,
    default: int,
) -> int:
    raw_value = data.get(key, default)
    if isinstance(raw_value, bool) or not isinstance(raw_value, int):
        raise EpisodeSpecError(
            f"{key}는 양의 정수여야 합니다."
        )
    if raw_value <= 0:
        raise EpisodeSpecError(
            f"{key}는 0보다 커야 합니다."
        )
    return raw_value


def _default_background_color(beat_type: str) -> str:
    return {
        "hook": "#14202B",
        "answer": "#223748",
        "story": "#314A5D",
        "fact": "#1C3040",
        "ending": "#101820",
    }[beat_type]
