from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class QuizTimelineBuildError(ValueError):
    """퀴즈 Remotion Timeline 생성 실패."""


class QuizTimelineBuilder:
    DEFAULT_FPS = 30
    DEFAULT_WIDTH = 1080
    DEFAULT_HEIGHT = 1920

    DEFAULT_BACKGROUND_COLOR = "#6FB382"
    DEFAULT_TITLE_COLOR = "#214F2A"
    DEFAULT_CAPTION_COLOR = "#214F2A"
    DEFAULT_ACCENT_COLOR = "#F6D25B"

    def load_quiz_scenes(
        self,
        scenes_path: Path,
    ) -> dict[str, Any]:
        resolved_path = scenes_path.resolve()

        if not resolved_path.exists():
            raise FileNotFoundError(
                f"Quiz Scene 파일이 없습니다: {resolved_path}"
            )

        if not resolved_path.is_file():
            raise QuizTimelineBuildError(
                f"Quiz Scene 경로가 파일이 아닙니다: {resolved_path}"
            )

        try:
            with resolved_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise QuizTimelineBuildError(
                "quiz_scenes.json 형식이 올바르지 않습니다: "
                f"{error}"
            ) from error

        if not isinstance(data, dict):
            raise QuizTimelineBuildError(
                "quiz_scenes.json 최상위 값은 객체여야 합니다."
            )

        return data

    def build_from_file(
        self,
        scenes_path: Path,
        output_path: Path,
    ) -> dict[str, Any]:
        quiz_scenes = self.load_quiz_scenes(
            scenes_path
        )

        timeline = self.build(
            quiz_scenes
        )

        self.write_output(
            timeline=timeline,
            output_path=output_path,
        )

        return timeline

    def build(
        self,
        quiz_scenes: dict[str, Any],
    ) -> dict[str, Any]:
        episode_id = self._require_text(
            quiz_scenes.get("episode_id"),
            "episode_id",
        )
        genre = self._require_text(
            quiz_scenes.get("genre"),
            "genre",
        )
        title = self._require_text(
            quiz_scenes.get("title"),
            "title",
        )

        if genre != "quiz":
            raise QuizTimelineBuildError(
                "genre는 quiz여야 합니다."
            )

        fps = self._require_positive_int(
            quiz_scenes.get(
                "fps",
                self.DEFAULT_FPS,
            ),
            "fps",
        )
        width = self._require_positive_int(
            quiz_scenes.get(
                "width",
                self.DEFAULT_WIDTH,
            ),
            "width",
        )
        height = self._require_positive_int(
            quiz_scenes.get(
                "height",
                self.DEFAULT_HEIGHT,
            ),
            "height",
        )

        raw_scenes = quiz_scenes.get("scenes")

        if not isinstance(raw_scenes, list):
            raise QuizTimelineBuildError(
                "scenes는 배열이어야 합니다."
            )

        if not raw_scenes:
            raise QuizTimelineBuildError(
                "Timeline으로 변환할 장면이 없습니다."
            )

        timeline_scenes: list[dict[str, Any]] = []
        current_start = 0.0

        for raw_scene in raw_scenes:
            if not isinstance(raw_scene, dict):
                raise QuizTimelineBuildError(
                    "각 Quiz Scene은 객체여야 합니다."
                )

            scene_type = self._require_text(
                raw_scene.get("scene_type"),
                "scene_type",
            )

            if scene_type == "countdown":
                countdown_scenes = (
                    self._build_countdown_timeline_scenes(
                        raw_scene=raw_scene,
                        start=current_start,
                    )
                )

                timeline_scenes.extend(
                    countdown_scenes
                )

                current_start = round(
                    current_start
                    + sum(
                        float(scene["duration"])
                        for scene in countdown_scenes
                    ),
                    3,
                )
                continue

            timeline_scene = (
                self._build_standard_timeline_scene(
                    raw_scene=raw_scene,
                    start=current_start,
                )
            )

            timeline_scenes.append(
                timeline_scene
            )

            current_start = round(
                current_start
                + float(timeline_scene["duration"]),
                3,
            )

        self._validate_timeline_scenes(
            timeline_scenes
        )

        return {
            "version": "8.1",
            "episodeId": episode_id,
            "channel": "quiz",
            "title": title,
            "fps": fps,
            "width": width,
            "height": height,
            "totalDuration": current_start,
            "theme": {
                "backgroundColor": (
                    self.DEFAULT_BACKGROUND_COLOR
                ),
                "titleColor": (
                    self.DEFAULT_TITLE_COLOR
                ),
                "captionColor": (
                    self.DEFAULT_CAPTION_COLOR
                ),
                "accentColor": (
                    self.DEFAULT_ACCENT_COLOR
                ),
            },
            "scenes": timeline_scenes,
        }

    def write_output(
        self,
        timeline: dict[str, Any],
        output_path: Path,
    ) -> None:
        resolved_path = output_path.resolve()

        resolved_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = resolved_path.with_suffix(
            resolved_path.suffix + ".tmp"
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            json.dump(
                timeline,
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")

        temporary_path.replace(
            resolved_path
        )

    def _build_standard_timeline_scene(
        self,
        *,
        raw_scene: dict[str, Any],
        start: float,
    ) -> dict[str, Any]:
        scene_id = self._require_text(
            raw_scene.get("id"),
            "scene.id",
        )
        scene_type = self._require_text(
            raw_scene.get("scene_type"),
            f"{scene_id}.scene_type",
        )
        duration = self._require_positive_number(
            raw_scene.get("duration"),
            f"{scene_id}.duration",
        )
        title = self._require_text(
            raw_scene.get("title"),
            f"{scene_id}.title",
        )
        display_text = self._require_text(
            raw_scene.get("display_text"),
            f"{scene_id}.display_text",
        )

        tts_text = raw_scene.get("tts_text")

        if tts_text is not None:
            tts_text = self._require_text(
                tts_text,
                f"{scene_id}.tts_text",
            )

        if scene_type == "intro":
            return self._create_timeline_scene(
                scene_id=scene_id,
                scene_type="intro",
                start=start,
                duration=duration,
                title=title,
                caption=display_text,
                narration=tts_text,
                transition="fade",
                transition_duration=0.25,
            )

        if scene_type == "question":
            return self._create_timeline_scene(
                scene_id=scene_id,
                scene_type="question",
                start=start,
                duration=duration,
                title=title,
                caption=display_text,
                narration=tts_text,
                transition="fade",
                transition_duration=0.2,
            )

        if scene_type == "answer":
            return self._create_timeline_scene(
                scene_id=scene_id,
                scene_type="answer",
                start=start,
                duration=duration,
                title="정답",
                caption=display_text,
                narration=tts_text,
                transition="zoom",
                transition_duration=0.2,
            )

        if scene_type == "ending":
            return self._create_timeline_scene(
                scene_id=scene_id,
                scene_type="ending",
                start=start,
                duration=duration,
                title=title,
                caption=display_text,
                narration=tts_text,
                transition="fade",
                transition_duration=0.25,
            )

        raise QuizTimelineBuildError(
            f"지원하지 않는 scene_type입니다: {scene_type}"
        )

    def _build_countdown_timeline_scenes(
        self,
        *,
        raw_scene: dict[str, Any],
        start: float,
    ) -> list[dict[str, Any]]:
        scene_id = self._require_text(
            raw_scene.get("id"),
            "countdown.id",
        )

        metadata = raw_scene.get(
            "metadata",
            {},
        )

        if not isinstance(metadata, dict):
            raise QuizTimelineBuildError(
                f"{scene_id}.metadata는 객체여야 합니다."
            )

        countdown_values = metadata.get(
            "countdown_values",
            [3, 2, 1],
        )

        if countdown_values != [3, 2, 1]:
            raise QuizTimelineBuildError(
                f"{scene_id}: 카운트다운 값은 "
                "[3, 2, 1]이어야 합니다."
            )

        result: list[dict[str, Any]] = []
        current_start = start

        for countdown_value in countdown_values:
            result.append(
                self._create_timeline_scene(
                    scene_id=(
                        f"{scene_id}_{countdown_value}"
                    ),
                    scene_type="countdown",
                    start=current_start,
                    duration=1.0,
                    title="정답 공개까지",
                    caption=str(countdown_value),
                    narration=None,
                    transition="cut",
                    transition_duration=0.0,
                    countdown_value=countdown_value,
                )
            )

            current_start = round(
                current_start + 1.0,
                3,
            )

        return result

    def _create_timeline_scene(
        self,
        *,
        scene_id: str,
        scene_type: str,
        start: float,
        duration: float,
        title: str,
        caption: str,
        narration: str | None,
        transition: str,
        transition_duration: float,
        countdown_value: int | None = None,
    ) -> dict[str, Any]:
        scene: dict[str, Any] = {
            "id": scene_id,
            "sceneType": scene_type,
            "start": round(start, 3),
            "duration": round(duration, 3),
            "title": title,
            "caption": caption,
            "backgroundColor": (
                self.DEFAULT_BACKGROUND_COLOR
            ),
            "media": {
                "type": "color",
                "fit": "cover",
                "position": "center",
            },
            "cameraMotion": "static",
            "transition": transition,
            "transitionDuration": transition_duration,
            "overlay": "none",
            "overlayOpacity": 0.0,
        }

        if narration:
            scene["narration"] = narration

        if countdown_value is not None:
            scene["countdownValue"] = countdown_value

        return scene

    def _validate_timeline_scenes(
        self,
        scenes: list[dict[str, Any]],
    ) -> None:
        scene_ids: set[str] = set()
        expected_start = 0.0

        for scene in scenes:
            scene_id = self._require_text(
                scene.get("id"),
                "timeline.scene.id",
            )

            if scene_id in scene_ids:
                raise QuizTimelineBuildError(
                    f"Timeline Scene ID가 중복되었습니다: "
                    f"{scene_id}"
                )

            scene_ids.add(scene_id)

            scene_type = self._require_text(
                scene.get("sceneType"),
                f"{scene_id}.sceneType",
            )

            if scene_type not in {
                "intro",
                "question",
                "countdown",
                "answer",
                "ending",
            }:
                raise QuizTimelineBuildError(
                    f"{scene_id}: 지원하지 않는 "
                    f"sceneType입니다: {scene_type}"
                )

            start = self._require_non_negative_number(
                scene.get("start"),
                f"{scene_id}.start",
            )
            duration = self._require_positive_number(
                scene.get("duration"),
                f"{scene_id}.duration",
            )

            if abs(start - expected_start) > 0.001:
                raise QuizTimelineBuildError(
                    f"{scene_id}: 시작 시간이 "
                    "연속되지 않습니다. "
                    f"예상: {expected_start}, "
                    f"실제: {start}"
                )

            expected_start = round(
                start + duration,
                3,
            )

    @staticmethod
    def _require_text(
        value: Any,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise QuizTimelineBuildError(
                f"{field_name}은 문자열이어야 합니다."
            )

        cleaned = " ".join(
            value.strip().split()
        )

        if not cleaned:
            raise QuizTimelineBuildError(
                f"{field_name}은 비어 있을 수 없습니다."
            )

        return cleaned

    @staticmethod
    def _require_positive_int(
        value: Any,
        field_name: str,
    ) -> int:
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value <= 0
        ):
            raise QuizTimelineBuildError(
                f"{field_name}은 1 이상의 정수여야 합니다."
            )

        return value

    @staticmethod
    def _require_positive_number(
        value: Any,
        field_name: str,
    ) -> float:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value <= 0
        ):
            raise QuizTimelineBuildError(
                f"{field_name}은 0보다 큰 숫자여야 합니다."
            )

        return float(value)

    @staticmethod
    def _require_non_negative_number(
        value: Any,
        field_name: str,
    ) -> float:
        if (
            not isinstance(value, (int, float))
            or isinstance(value, bool)
            or value < 0
        ):
            raise QuizTimelineBuildError(
                f"{field_name}은 0 이상의 숫자여야 합니다."
            )

        return float(value)