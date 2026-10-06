from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from duration_planner import DurationPlanner
from story_compiler import StoryCompiler
from story_graph import Story
from timeline_scheduler import TimelineScheduler
from timeline_schema import Timeline


@dataclass(frozen=True)
class FactoryBuildResult:
    """
    Factory Core 빌드 결과입니다.

    timeline:
        Remotion Renderer에 전달할 최종 Timeline

    scene_count:
        생성된 Scene 수

    total_duration:
        최종 Timeline 전체 길이
    """

    timeline: Timeline
    scene_count: int
    total_duration: float


class FactoryCore:
    """
    Story를 최종 Timeline으로 변환하는 Factory Core 진입점입니다.

    외부 코드와 Plugin은 DurationPlanner, TimelineScheduler,
    StoryCompiler의 내부 실행 순서를 알 필요가 없습니다.

    사용 예:

        timeline = FactoryCore().build(story)

    내부 처리:

        Story
        -> DurationPlanner
        -> TimelineScheduler
        -> StoryCompiler
        -> Timeline

    FactoryCore는 장르를 알지 않습니다.
    장르별 Story 생성 책임은 Plugin에 있습니다.
    """

    def __init__(
        self,
        *,
        duration_planner: Optional[
            DurationPlanner
        ] = None,
        timeline_scheduler: Optional[
            TimelineScheduler
        ] = None,
    ) -> None:
        self._duration_planner = (
            duration_planner
        )

        self._timeline_scheduler = (
            timeline_scheduler
            or TimelineScheduler()
        )

    def build(
        self,
        story: Story,
    ) -> Timeline:
        """
        Story를 검증하고 최종 Timeline을 생성합니다.
        """

        compiler = StoryCompiler(
            duration_planner=(
                self._duration_planner
            ),
            timeline_scheduler=(
                self._timeline_scheduler
            ),
        )

        return compiler.compile(story)

    def build_with_result(
        self,
        story: Story,
    ) -> FactoryBuildResult:
        """
        Timeline과 빌드 요약 정보를 함께 반환합니다.
        """

        timeline = self.build(story)

        return FactoryBuildResult(
            timeline=timeline,
            scene_count=len(
                timeline.scenes
            ),
            total_duration=(
                timeline.duration
            ),
        )
