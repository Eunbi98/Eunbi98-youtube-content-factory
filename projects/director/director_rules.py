from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional


SceneType = Literal[
    "hook",
    "answer",
    "story",
    "fact",
    "ending",
]

CameraMotion = Literal[
    "static",
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right",
    "pan_up",
    "pan_down",
    "zoom_in_left",
    "zoom_in_right",
    "zoom_in_up",
    "zoom_in_down",
]

TransitionType = Literal[
    "cut",
    "fade",
    "slide_left",
    "slide_right",
    "zoom",
]

OverlayType = Literal[
    "none",
    "cinematic",
    "vignette",
    "dark",
]


@dataclass(frozen=True)
class DirectionPreset:
    camera_motion: CameraMotion
    transition: TransitionType
    transition_duration: float
    overlay: OverlayType
    overlay_opacity: float


# 각 장면 역할에 맞는 기본 연출 규칙입니다.
BASE_PRESETS: dict[SceneType, DirectionPreset] = {
    "hook": DirectionPreset(
        camera_motion="zoom_in",
        transition="fade",
        transition_duration=0.30,
        overlay="cinematic",
        overlay_opacity=1.0,
    ),
    "answer": DirectionPreset(
        camera_motion="pan_right",
        transition="cut",
        transition_duration=0.20,
        overlay="cinematic",
        overlay_opacity=1.0,
    ),
    "story": DirectionPreset(
        camera_motion="pan_left",
        transition="fade",
        transition_duration=0.30,
        overlay="cinematic",
        overlay_opacity=1.0,
    ),
    "fact": DirectionPreset(
        camera_motion="zoom_in_right",
        transition="slide_left",
        transition_duration=0.30,
        overlay="vignette",
        overlay_opacity=1.0,
    ),
    "ending": DirectionPreset(
        camera_motion="zoom_out",
        transition="fade",
        transition_duration=0.35,
        overlay="dark",
        overlay_opacity=1.0,
    ),
}


def direct_scene(
    *,
    scene_type: SceneType,
    scene_index: int,
    previous_motion: Optional[CameraMotion] = None,
) -> DirectionPreset:
    """
    장면 역할과 앞 장면의 움직임을 참고해 연출값을 결정합니다.

    같은 cameraMotion이 반복될 경우 대체 모션으로 변경해
    영상 움직임이 단조로워지는 것을 방지합니다.
    """

    preset = BASE_PRESETS[scene_type]

    camera_motion = preset.camera_motion
    transition = preset.transition

    if previous_motion == camera_motion:
        camera_motion = _get_alternative_motion(
            scene_type=scene_type,
            scene_index=scene_index,
            previous_motion=previous_motion,
        )

    # 첫 장면은 앞 장면이 없으므로 fade 또는 cut만 사용합니다.
    if scene_index == 0:
        transition = "fade"

    return DirectionPreset(
        camera_motion=camera_motion,
        transition=transition,
        transition_duration=preset.transition_duration,
        overlay=preset.overlay,
        overlay_opacity=preset.overlay_opacity,
    )


def _get_alternative_motion(
    *,
    scene_type: SceneType,
    scene_index: int,
    previous_motion: CameraMotion,
) -> CameraMotion:
    """
    반복되는 카메라 움직임을 피하기 위한 대체 규칙입니다.
    """

    alternatives: dict[SceneType, tuple[CameraMotion, ...]] = {
        "hook": (
            "zoom_in",
            "zoom_in_left",
            "zoom_in_right",
        ),
        "answer": (
            "pan_right",
            "pan_left",
            "zoom_in_right",
        ),
        "story": (
            "pan_left",
            "pan_right",
            "zoom_in_left",
        ),
        "fact": (
            "zoom_in_right",
            "zoom_in_left",
            "pan_up",
        ),
        "ending": (
            "zoom_out",
            "static",
            "pan_down",
        ),
    }

    candidates = alternatives[scene_type]

    valid_candidates = [
        candidate
        for candidate in candidates
        if candidate != previous_motion
    ]

    if not valid_candidates:
        return "static"

    return valid_candidates[
        scene_index % len(valid_candidates)
    ]