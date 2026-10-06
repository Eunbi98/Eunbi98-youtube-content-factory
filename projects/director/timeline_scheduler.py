from __future__ import annotations

from dataclasses import dataclass

from story_graph import Beat


@dataclass(frozen=True)
class ScheduledScene:
    """
    Duration 계산이 완료된 Beat에
    Timeline 시작 시간을 부여한 결과입니다.

    Beat 자체에는 시간 정보를 저장하지 않습니다.
    start와 duration은 Factory Core의 Scheduler가 관리합니다.
    """

    beat: Beat
    start: float
    duration: float


@dataclass(frozen=True)
class TimelineSchedule:
    """
    TimelineScheduler의 최종 결과입니다.

    scenes:
        시작 시간과 duration이 계산된 장면 목록

    total_duration:
        마지막 장면 종료 시간을 기준으로 계산된
        전체 Timeline 길이
    """

    scenes: list[ScheduledScene]
    total_duration: float


class TimelineScheduler:
    """
    Duration Planner가 계산한 장면 길이를 사용해
    각 장면의 시작 시간과 전체 Timeline 길이를 계산합니다.

    계산 규칙:

    첫 번째 장면:
        start = 0

    이후 장면:
        start = 이전 장면 start + 이전 장면 duration

    Timeline 전체 길이:
        마지막 장면 start + 마지막 장면 duration

    TimelineScheduler는 장르와 Story 내용을 알지 않습니다.
    전달받은 Beat와 duration의 순서만 기준으로 동작합니다.
    """

    def __init__(
        self,
        *,
        precision: int = 3,
    ) -> None:
        if precision < 0:
            raise ValueError(
                "precision은 0 이상이어야 합니다."
            )

        self._precision = precision

    def schedule(
        self,
        *,
        beats: list[Beat],
        durations: list[float],
    ) -> TimelineSchedule:
        """
        Beat 목록과 duration 목록을 받아
        각 장면의 start를 자동 계산합니다.
        """

        self._validate_inputs(
            beats=beats,
            durations=durations,
        )

        scheduled_scenes: list[ScheduledScene] = []
        current_start = 0.0

        for beat, duration in zip(
            beats,
            durations,
            strict=True,
        ):
            normalized_duration = self._round_time(
                duration
            )

            normalized_start = self._round_time(
                current_start
            )

            scheduled_scenes.append(
                ScheduledScene(
                    beat=beat,
                    start=normalized_start,
                    duration=normalized_duration,
                )
            )

            current_start = self._round_time(
                normalized_start
                + normalized_duration
            )

        return TimelineSchedule(
            scenes=scheduled_scenes,
            total_duration=self._round_time(
                current_start
            ),
        )

    def _validate_inputs(
        self,
        *,
        beats: list[Beat],
        durations: list[float],
    ) -> None:
        if not beats:
            raise ValueError(
                "Timeline을 구성하려면 "
                "최소 하나 이상의 Beat가 필요합니다."
            )

        if len(beats) != len(durations):
            raise ValueError(
                "Beat 개수와 duration 개수가 "
                "일치해야 합니다. "
                f"beats={len(beats)}, "
                f"durations={len(durations)}"
            )

        for index, duration in enumerate(
            durations,
            start=1,
        ):
            if duration <= 0:
                raise ValueError(
                    f"Scene {index}: duration은 "
                    "0보다 커야 합니다."
                )

    def _round_time(
        self,
        value: float,
    ) -> float:
        """
        모든 Timeline 시간을 동일한 정밀도로 정규화합니다.

        Python 부동소수점 오차로 인해
        다음 장면 시작 시간이 이전 장면 종료 시간과
        미세하게 달라지는 문제를 방지합니다.
        """

        return round(
            value,
            self._precision,
        )
