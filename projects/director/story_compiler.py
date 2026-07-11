from __future__ import annotations

from timeline_schema import (
    Media,
    Scene,
    Timeline,
    TimelineTheme,
)
from story_graph import Beat, Story


class StoryCompiler:
    """
    Story Graph를 Director가 처리할 수 있는
    Timeline Scene 구조로 변환합니다.

    현재 Patch에서는 다음 값을 자동 생성합니다.

    - scene id
    - scene start
    - 전체 timeline duration
    - StoryMedia → Media 변환

    cameraMotion, transition, overlay는
    timeline_schema 내부 Director Rule Engine이
    자동으로 결정합니다.
    """

    def compile(self, story: Story) -> Timeline:
        self._validate_story(story)

        scenes: list[Scene] = []
        current_start = 0.0

        for index, beat in enumerate(
            story.beats,
            start=1,
        ):
            scene = self._compile_beat(
                beat=beat,
                scene_index=index,
                start=current_start,
            )

            scenes.append(scene)

            current_start += beat.duration

        total_duration = round(
            current_start,
            3,
        )

        return Timeline(
            version="5.2",
            episode_id=story.episode_id,
            title=story.title,
            fps=story.fps,
            width=story.width,
            height=story.height,
            duration=total_duration,
            bgm=story.bgm,
            voice=story.voice,
            theme=TimelineTheme(
                background_color=(
                    story.background_color
                ),
                title_color=story.title_color,
                caption_color=(
                    story.caption_color
                ),
                accent_color=story.accent_color,
            ),
            scenes=scenes,
        )

    def _compile_beat(
        self,
        *,
        beat: Beat,
        scene_index: int,
        start: float,
    ) -> Scene:
        scene_id = (
            f"scene_{scene_index:03d}"
        )

        media = Media(
            type=beat.media.type,
            src=beat.media.src,
            fit=beat.media.fit,
            position=beat.media.position,
        )

        return Scene(
            id=scene_id,
            type=beat.type,
            start=round(start, 3),
            duration=round(
                beat.duration,
                3,
            ),
            title=beat.title.strip(),
            narration=(
                beat.narration.strip()
            ),
            subtitle=(
                beat.subtitle.strip()
            ),
            media=media,
            keywords=list(beat.keywords),
            background_color=(
                beat.background_color
            ),
        )

    def _validate_story(
        self,
        story: Story,
    ) -> None:
        if not story.episode_id.strip():
            raise ValueError(
                "Story episode_id는 "
                "비어 있을 수 없습니다."
            )

        if not story.title.strip():
            raise ValueError(
                "Story title은 "
                "비어 있을 수 없습니다."
            )

        if not story.beats:
            raise ValueError(
                "Story에는 최소 하나 이상의 "
                "Beat가 필요합니다."
            )

        if story.fps <= 0:
            raise ValueError(
                "Story fps는 1 이상이어야 합니다."
            )

        if (
            story.width <= 0
            or story.height <= 0
        ):
            raise ValueError(
                "Story width와 height는 "
                "1 이상이어야 합니다."
            )

        for index, beat in enumerate(
            story.beats,
            start=1,
        ):
            self._validate_beat(
                beat=beat,
                beat_index=index,
            )

    def _validate_beat(
        self,
        *,
        beat: Beat,
        beat_index: int,
    ) -> None:
        prefix = f"Beat {beat_index}"

        if beat.duration <= 0:
            raise ValueError(
                f"{prefix}: duration은 "
                "0보다 커야 합니다."
            )

        if not beat.title.strip():
            raise ValueError(
                f"{prefix}: title은 "
                "비어 있을 수 없습니다."
            )

        if not beat.narration.strip():
            raise ValueError(
                f"{prefix}: narration은 "
                "비어 있을 수 없습니다."
            )

        if not beat.subtitle.strip():
            raise ValueError(
                f"{prefix}: subtitle은 "
                "비어 있을 수 없습니다."
            )

        if (
            beat.media.type
            in {"image", "video"}
            and not beat.media.src
        ):
            raise ValueError(
                f"{prefix}: "
                f"{beat.media.type} media에는 "
                "src가 필요합니다."
            )