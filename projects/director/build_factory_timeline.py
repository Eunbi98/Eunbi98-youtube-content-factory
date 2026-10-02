from __future__ import annotations

from build_timeline import build_ep008_story
from factory_core import FactoryCore
from timeline_schema import save_timeline


def build_ep008_with_factory() -> None:
    """
    EP008 Story를 FactoryCore 한 번의 호출로
    Timeline으로 변환하고 저장합니다.
    """

    story = build_ep008_story()

    factory = FactoryCore()

    result = factory.build_with_result(
        story
    )

    output_path = (
        "projects/episodes/ep008/"
        "timeline.json"
    )

    save_timeline(
        result.timeline,
        output_path,
    )

    print(
        "EP008 Factory Core 실행 완료"
    )
    print(
        f"Scene 수: {result.scene_count}"
    )
    print(
        "전체 길이: "
        f"{result.total_duration}초"
    )
    print(
        f"출력 경로: {output_path}"
    )


if __name__ == "__main__":
    build_ep008_with_factory()
