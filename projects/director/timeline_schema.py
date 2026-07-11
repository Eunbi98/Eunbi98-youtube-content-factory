from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Optional

from director_rules import (
    CameraMotion,
    OverlayType,
    SceneType,
    TransitionType,
    direct_scene,
)


MediaType = Literal[
    "image",
    "video",
    "color",
]


@dataclass
class Media:
    type: MediaType
    src: Optional[str] = None
    fit: Literal["cover", "contain"] = "cover"
    position: str = "center center"

    def to_remotion_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "type": self.type,
            "fit": self.fit,
            "position": self.position,
        }

        if self.src:
            data["src"] = self.src.lstrip("/\\")

        return data


@dataclass
class Scene:
    id: str
    type: SceneType
    start: float
    duration: float
    title: str
    narration: str
    subtitle: str
    media: Media
    keywords: list[str]
    background_color: str = "#111111"
    camera_motion: Optional[CameraMotion] = None
    transition: Optional[TransitionType] = None
    transition_duration: Optional[float] = None
    overlay: Optional[OverlayType] = None
    overlay_opacity: Optional[float] = None

    def to_remotion_dict(
        self,
        *,
        scene_index: int,
        previous_motion: Optional[CameraMotion],
    ) -> dict[str, Any]:
        direction = direct_scene(
            scene_type=self.type,
            scene_index=scene_index,
            previous_motion=previous_motion,
        )

        resolved_camera_motion = (
            self.camera_motion
            or direction.camera_motion
        )

        resolved_transition = (
            self.transition
            or direction.transition
        )

        resolved_transition_duration = (
            self.transition_duration
            if self.transition_duration is not None
            else direction.transition_duration
        )

        resolved_overlay = (
            self.overlay
            or direction.overlay
        )

        resolved_overlay_opacity = (
            self.overlay_opacity
            if self.overlay_opacity is not None
            else direction.overlay_opacity
        )

        return {
            "id": self.id,
            "start": round(
                self.start,
                3,
            ),
            "duration": round(
                self.duration,
                3,
            ),
            "title": self.title,
            "narration": self.narration,
            "caption": self.subtitle,
            "backgroundColor": (
                self.background_color
            ),
            "media": (
                self.media.to_remotion_dict()
            ),
            "cameraMotion": (
                resolved_camera_motion
            ),
            "transition": (
                resolved_transition
            ),
            "transitionDuration": round(
                resolved_transition_duration,
                3,
            ),
            "overlay": resolved_overlay,
            "overlayOpacity": round(
                resolved_overlay_opacity,
                3,
            ),
        }


@dataclass
class TimelineTheme:
    background_color: str = "#000000"
    title_color: str = "#7CFFB2"
    caption_color: str = "#FFFFFF"
    accent_color: str = "#7CFFB2"

    def to_remotion_dict(
        self,
    ) -> dict[str, str]:
        return {
            "backgroundColor": (
                self.background_color
            ),
            "titleColor": (
                self.title_color
            ),
            "captionColor": (
                self.caption_color
            ),
            "accentColor": (
                self.accent_color
            ),
        }


@dataclass
class Timeline:
    version: str
    episode_id: str
    title: str
    fps: int
    width: int
    height: int
    duration: float
    bgm: Optional[str]
    voice: Optional[str]
    scenes: list[Scene]
    theme: Optional[TimelineTheme] = None

    def validate(self) -> None:
        """
        Timeline 데이터를 검증합니다.

        시간 비교 시 Python 부동소수점 오차로 인해
        정상적인 장면이 겹친 것으로 판단되지 않도록
        작은 허용 오차를 적용합니다.
        """

        if not self.episode_id.strip():
            raise ValueError(
                "episode_id는 비어 있을 수 없습니다."
            )

        if not self.title.strip():
            raise ValueError(
                "title은 비어 있을 수 없습니다."
            )

        if self.fps <= 0:
            raise ValueError(
                "fps는 1 이상이어야 합니다."
            )

        if (
            self.width <= 0
            or self.height <= 0
        ):
            raise ValueError(
                "width와 height는 1 이상이어야 합니다."
            )

        if not self.scenes:
            raise ValueError(
                "최소 한 개 이상의 scene이 필요합니다."
            )

        time_tolerance = 0.001
        previous_end = 0.0

        for index, scene in enumerate(
            self.scenes
        ):
            if scene.duration <= 0:
                raise ValueError(
                    f"{scene.id}: duration은 "
                    "0보다 커야 합니다."
                )

            if scene.start < 0:
                raise ValueError(
                    f"{scene.id}: start는 "
                    "0 이상이어야 합니다."
                )

            if not scene.narration.strip():
                raise ValueError(
                    f"{scene.id}: narration은 "
                    "비어 있을 수 없습니다."
                )

            if (
                index > 0
                and scene.start
                < previous_end - time_tolerance
            ):
                raise ValueError(
                    f"{scene.id}: 이전 장면과 "
                    "시간이 겹칩니다.\n"
                    f"start={scene.start}, "
                    f"previous_end={previous_end}"
                )

            previous_end = round(
                scene.start + scene.duration,
                3,
            )

        if (
            self.duration
            < previous_end - time_tolerance
        ):
            raise ValueError(
                "Timeline duration이 마지막 장면의 "
                "종료 시간보다 짧습니다.\n"
                f"duration={self.duration}, "
                f"last_scene_end={previous_end}"
            )

    def to_remotion_dict(
        self,
    ) -> dict[str, Any]:
        self.validate()

        theme = (
            self.theme
            or TimelineTheme()
        )

        rendered_scenes: list[
            dict[str, Any]
        ] = []

        previous_motion: Optional[
            CameraMotion
        ] = None

        for index, scene in enumerate(
            self.scenes
        ):
            rendered_scene = (
                scene.to_remotion_dict(
                    scene_index=index,
                    previous_motion=(
                        previous_motion
                    ),
                )
            )

            rendered_scenes.append(
                rendered_scene
            )

            previous_motion = (
                rendered_scene[
                    "cameraMotion"
                ]
            )

        data: dict[str, Any] = {
            "version": self.version,
            "episodeId": (
                self.episode_id.upper()
            ),
            "title": self.title,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "totalDuration": round(
                self.duration,
                3,
            ),
            "theme": (
                theme.to_remotion_dict()
            ),
            "scenes": rendered_scenes,
        }

        if self.bgm:
            data["bgm"] = self.bgm

        if self.voice:
            data["voice"] = self.voice

        return data


def save_timeline(
    timeline: Timeline,
    output_path: str | Path,
) -> None:
    path = Path(output_path)

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data = timeline.to_remotion_dict()

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")