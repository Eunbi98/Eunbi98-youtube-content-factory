from __future__ import annotations

from dataclasses import dataclass
import math
import re

from story_graph import Beat, BeatType


@dataclass(frozen=True)
class DurationRule:
    """
    장면 유형별 duration 계산 규칙입니다.

    minimum:
        해당 장면 유형이 가질 수 있는 최소 길이

    maximum:
        해당 장면 유형이 가질 수 있는 최대 길이

    padding:
        음성 길이에 추가하는 화면 여유 시간
    """

    minimum: float
    maximum: float
    padding: float


DEFAULT_DURATION_RULES: dict[
    BeatType,
    DurationRule,
] = {
    "hook": DurationRule(
        minimum=3.0,
        maximum=6.0,
        padding=0.35,
    ),
    "answer": DurationRule(
        minimum=4.0,
        maximum=8.0,
        padding=0.45,
    ),
    "story": DurationRule(
        minimum=5.0,
        maximum=10.0,
        padding=0.55,
    ),
    "fact": DurationRule(
        minimum=4.0,
        maximum=8.0,
        padding=0.45,
    ),
    "ending": DurationRule(
        minimum=3.5,
        maximum=7.0,
        padding=0.65,
    ),
}


class DurationPlanner:
    """
    narration 길이와 장면 유형을 기준으로
    Scene duration을 자동 계산합니다.

    계산 순서:

    1. narration의 발화 단위 수를 계산합니다.
    2. 초당 발화 단위 수를 기준으로 예상 음성 길이를 계산합니다.
    3. 장면 유형별 padding을 추가합니다.
    4. 장면 유형별 최소/최대 길이 범위로 보정합니다.
    5. 영상 프레임 경계에 맞춰 duration을 정렬합니다.
    """

    def __init__(
        self,
        *,
        units_per_second: float = 6.2,
        fps: int = 30,
        rules: dict[
            BeatType,
            DurationRule,
        ] | None = None,
    ) -> None:
        if units_per_second <= 0:
            raise ValueError(
                "units_per_second는 "
                "0보다 커야 합니다."
            )

        if fps <= 0:
            raise ValueError(
                "fps는 1 이상이어야 합니다."
            )

        self._units_per_second = (
            units_per_second
        )
        self._fps = fps
        self._rules = (
            rules
            if rules is not None
            else DEFAULT_DURATION_RULES
        )

        self._validate_rules()

    def plan(
        self,
        beat: Beat,
    ) -> float:
        """
        단일 Beat의 duration을 계산합니다.
        """

        narration = beat.narration.strip()

        if not narration:
            raise ValueError(
                "Duration을 계산하려면 "
                "narration이 필요합니다."
            )

        rule = self._rules.get(beat.type)

        if rule is None:
            raise ValueError(
                "지원하지 않는 Beat type입니다: "
                f"{beat.type}"
            )

        speech_units = self._count_speech_units(
            narration
        )

        estimated_speech_duration = (
            speech_units
            / self._units_per_second
        )

        estimated_duration = (
            estimated_speech_duration
            + rule.padding
        )

        clamped_duration = self._clamp(
            estimated_duration,
            minimum=rule.minimum,
            maximum=rule.maximum,
        )

        return self._align_to_frame(
            clamped_duration
        )

    def plan_many(
        self,
        beats: list[Beat],
    ) -> list[float]:
        """
        여러 Beat의 duration을 순서대로 계산합니다.
        """

        return [
            self.plan(beat)
            for beat in beats
        ]

    def _count_speech_units(
        self,
        narration: str,
    ) -> int:
        """
        narration의 발화 단위를 계산합니다.

        한글 음절, 영문자, 숫자는 각각 하나의 발화 단위로 처리합니다.
        공백과 일반 문장부호는 제외합니다.

        쉼표, 마침표, 물음표, 느낌표 등은 실제 TTS에서
        짧은 정지 시간을 만들기 때문에 별도의 pause 단위로 반영합니다.
        """

        spoken_characters = re.findall(
            r"[가-힣A-Za-z0-9]",
            narration,
        )

        sentence_pauses = re.findall(
            r"[.!?。！？]",
            narration,
        )

        short_pauses = re.findall(
            r"[,，:;·]",
            narration,
        )

        unit_count = len(spoken_characters)

        unit_count += (
            len(sentence_pauses) * 3
        )

        unit_count += (
            len(short_pauses) * 1
        )

        return max(unit_count, 1)

    def _align_to_frame(
        self,
        duration: float,
    ) -> float:
        """
        duration을 프레임 단위에 맞춰 올림 처리합니다.

        음성이 장면 종료 전에 잘리는 것을 막기 위해
        가장 가까운 프레임으로 내리지 않고 올림합니다.
        """

        frame_count = math.ceil(
            duration * self._fps
        )

        aligned_duration = (
            frame_count / self._fps
        )

        return round(
            aligned_duration,
            3,
        )

    @staticmethod
    def _clamp(
        value: float,
        *,
        minimum: float,
        maximum: float,
    ) -> float:
        return max(
            minimum,
            min(value, maximum),
        )

    def _validate_rules(self) -> None:
        required_types: set[BeatType] = {
            "hook",
            "answer",
            "story",
            "fact",
            "ending",
        }

        missing_types = (
            required_types
            - set(self._rules.keys())
        )

        if missing_types:
            missing = ", ".join(
                sorted(missing_types)
            )

            raise ValueError(
                "Duration rule이 없습니다: "
                f"{missing}"
            )

        for beat_type, rule in (
            self._rules.items()
        ):
            if rule.minimum <= 0:
                raise ValueError(
                    f"{beat_type}: minimum은 "
                    "0보다 커야 합니다."
                )

            if rule.maximum < rule.minimum:
                raise ValueError(
                    f"{beat_type}: maximum은 "
                    "minimum 이상이어야 합니다."
                )

            if rule.padding < 0:
                raise ValueError(
                    f"{beat_type}: padding은 "
                    "0 이상이어야 합니다."
                )