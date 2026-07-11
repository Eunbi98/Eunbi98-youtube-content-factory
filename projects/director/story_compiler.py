from __future__ import annotations

from duration_planner import DurationPlanner
from story_graph import Beat, Story
from timeline_scheduler import (
    ScheduledScene,
    TimelineScheduler,
)
from timeline_schema import (
    Media,
    Scene,
    Timeline,
    TimelineTheme,
)


class StoryCompiler:
    """
    Story Graph를 Timeline 구조로 변환합니다.

    StoryCompiler의 책임:

    - Story 검증
    - Beat를 Scene으로 변환
    - Timeline 객체 생성

    StoryCompiler가 담당하지 않는 책임:

    - Scene duration 계산
      -> DurationPlanner

    - Scene start 계산
      -> TimelineScheduler

    - 카메라, 전환, 오버레이 결정
      -> Director Rule Engine

    Patch 5-4부터 StoryCompiler는 직접 시간을 계산하지 않습니다.
    """

    def __init__(
        self,
        *,
        duration_planner: (
            DurationPlanner | None
        ) = None,
        timeline_scheduler: (
            TimelineScheduler | None
        ) = None,
    ) -> None:
        self._duration_planner = duration_planner
        self._timeline_scheduler = (
            timeline_scheduler
            or TimelineScheduler()
        )

    def compile(
        self,
        story: Story,
    ) -> Timeline:
        """
        Story를 완성된 Timeline으로 변환합니다.
        """

        self._validate_story(story)

        duration_planner = (
            self._duration_planner
            or DurationPlanner(
                fps=story.fps,
            )
        )

        durations = duration_planner.plan_many(
            story.beats
        )

        schedule = (
            self._timeline_scheduler.schedule(
                beats=story.beats,
                durations=durations,
            )
        )

        scenes = [
            self._compile_scheduled_scene(
                scheduled_scene=scheduled_scene,
                scene_index=index,
            )
            for index, scheduled_scene
            in enumerate(
                schedule.scenes,
                start=1,
            )
        ]

        timeline = Timeline(
            version="5.4",
            episode_id=story.episode_id,
            title=story.title,
            fps=story.fps,
            width=story.width,
            height=story.height,
            duration=schedule.total_duration,
            bgm=story.bgm,
            voice=story.voice,
            theme=TimelineTheme(
                background_color=(
                    story.background_color
                ),
                title_color=(
                    story.title_color
                ),
                caption_color=(
                    story.caption_color
                ),
                accent_color=(
                    story.accent_color
                ),
            ),
            scenes=scenes,
        )

        timeline.validate()

        return timeline

    def _compile_scheduled_scene(
        self,
        *,
        scheduled_scene: ScheduledScene,
        scene_index: int,
    ) -> Scene:
        """
        TimelineScheduler가 계산한 시간 정보를 사용해
        하나의 ScheduledScene을 Timeline Scene으로 변환합니다.
        """

        beat = scheduled_scene.beat
        scene_id = f"scene_{scene_index:03d}"

        media = Media(
            type=beat.media.type,
            src=beat.media.src,
            fit=beat.media.fit,
            position=beat.media.position,
        )

        return Scene(
            id=scene_id,
            type=beat.type,
            start=scheduled_scene.start,
            duration=scheduled_scene.duration,
            title=beat.title.strip(),
            narration=beat.narration.strip(),
            subtitle=beat.subtitle.strip(),
            media=media,
            keywords=list(
                beat.keywords
            ),
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
                "Story fps는 "
                "1 이상이어야 합니다."
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
