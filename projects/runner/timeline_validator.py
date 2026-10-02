from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class TimelineValidationError(ValueError):
    """timeline.json 구조가 올바르지 않을 때 발생합니다."""


@dataclass(frozen=True)
class TimelineSummary:
    episode_id: str
    title: str
    fps: int
    width: int
    height: int
    total_duration: float
    scene_count: int


def _require(
    condition: bool,
    message: str,
) -> None:
    if not condition:
        raise TimelineValidationError(message)


def load_and_validate_timeline(
    timeline_path: Path,
) -> tuple[dict[str, Any], TimelineSummary]:
    if not timeline_path.exists():
        raise TimelineValidationError(
            f"timeline.json을 찾을 수 없습니다: {timeline_path}"
        )

    try:
        raw_text = timeline_path.read_text(
            encoding="utf-8"
        )
        data = json.loads(raw_text)
    except UnicodeDecodeError as exc:
        raise TimelineValidationError(
            "timeline.json이 UTF-8 형식이 아닙니다."
        ) from exc
    except json.JSONDecodeError as exc:
        raise TimelineValidationError(
            "timeline.json JSON 문법 오류: "
            f"{exc.msg} (줄 {exc.lineno}, 열 {exc.colno})"
        ) from exc

    _require(
        isinstance(data, dict),
        "timeline 최상위 값은 객체여야 합니다.",
    )

    required_fields = (
        "episodeId",
        "title",
        "fps",
        "width",
        "height",
        "totalDuration",
        "scenes",
    )

    for field in required_fields:
        _require(
            field in data,
            f"필수 항목이 없습니다: {field}",
        )

    episode_id = data["episodeId"]
    title = data["title"]
    fps = data["fps"]
    width = data["width"]
    height = data["height"]
    total_duration = data["totalDuration"]
    scenes = data["scenes"]

    _require(
        isinstance(episode_id, str)
        and bool(episode_id.strip()),
        "episodeId는 빈 문자열이 아니어야 합니다.",
    )
    _require(
        isinstance(title, str)
        and bool(title.strip()),
        "title은 빈 문자열이 아니어야 합니다.",
    )
    _require(
        isinstance(fps, int) and fps > 0,
        "fps는 1 이상의 정수여야 합니다.",
    )
    _require(
        isinstance(width, int) and width > 0,
        "width는 1 이상의 정수여야 합니다.",
    )
    _require(
        isinstance(height, int) and height > 0,
        "height는 1 이상의 정수여야 합니다.",
    )
    _require(
        isinstance(total_duration, (int, float))
        and total_duration > 0,
        "totalDuration은 0보다 커야 합니다.",
    )
    _require(
        isinstance(scenes, list) and len(scenes) > 0,
        "scenes는 하나 이상의 장면을 포함해야 합니다.",
    )

    seen_ids: set[str] = set()
    previous_end = 0.0

    for index, scene in enumerate(scenes, start=1):
        _require(
            isinstance(scene, dict),
            f"{index}번째 scene은 객체여야 합니다.",
        )

        for field in (
            "id",
            "start",
            "duration",
            "caption",
            "media",
        ):
            _require(
                field in scene,
                f"{index}번째 scene에 {field}가 없습니다.",
            )

        scene_id = scene["id"]
        start = scene["start"]
        duration = scene["duration"]
        caption = scene["caption"]
        media = scene["media"]

        _require(
            isinstance(scene_id, str)
            and bool(scene_id.strip()),
            f"{index}번째 scene id가 올바르지 않습니다.",
        )
        _require(
            scene_id not in seen_ids,
            f"scene id가 중복되었습니다: {scene_id}",
        )
        seen_ids.add(scene_id)

        _require(
            isinstance(start, (int, float))
            and start >= 0,
            f"{scene_id}의 start가 올바르지 않습니다.",
        )
        _require(
            isinstance(duration, (int, float))
            and duration > 0,
            f"{scene_id}의 duration은 0보다 커야 합니다.",
        )
        _require(
            isinstance(caption, str),
            f"{scene_id}의 caption은 문자열이어야 합니다.",
        )
        _require(
            isinstance(media, dict),
            f"{scene_id}의 media는 객체여야 합니다.",
        )
        _require(
            "type" in media,
            f"{scene_id}의 media.type이 없습니다.",
        )

        start_value = float(start)
        duration_value = float(duration)

        _require(
            start_value >= previous_end - 0.001,
            f"{scene_id}가 이전 scene과 겹칩니다.",
        )

        previous_end = start_value + duration_value

    _require(
        previous_end <= float(total_duration) + 0.05,
        "마지막 scene 종료 시간이 totalDuration을 초과합니다.",
    )

    summary = TimelineSummary(
        episode_id=episode_id,
        title=title,
        fps=fps,
        width=width,
        height=height,
        total_duration=float(total_duration),
        scene_count=len(scenes),
    )

    return data, summary
