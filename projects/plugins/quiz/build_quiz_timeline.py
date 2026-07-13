from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from projects.plugins.quiz.quiz_timeline_builder import (  # noqa: E402
    QuizTimelineBuildError,
    QuizTimelineBuilder,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "quiz_scenes.json을 Remotion용 "
            "timeline.json으로 변환합니다."
        )
    )

    parser.add_argument(
        "--episode-id",
        default="ep010",
        help="에피소드 ID",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default=None,
        help="quiz_scenes.json 경로",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default=None,
        help="timeline.json 출력 경로",
    )

    return parser


def resolve_paths(
    episode_id: str,
    input_value: str | None,
    output_value: str | None,
) -> tuple[Path, Path]:
    normalized_episode_id = (
        episode_id.strip()
    )

    if not normalized_episode_id:
        raise QuizTimelineBuildError(
            "episode_id는 비어 있을 수 없습니다."
        )

    episode_dir = (
        PROJECT_ROOT
        / "projects"
        / "episodes"
        / normalized_episode_id
    )

    input_path = (
        Path(input_value)
        if input_value
        else episode_dir / "quiz_scenes.json"
    )

    output_path = (
        Path(output_value)
        if output_value
        else episode_dir / "timeline.json"
    )

    if not input_path.is_absolute():
        input_path = (
            PROJECT_ROOT / input_path
        )

    if not output_path.is_absolute():
        output_path = (
            PROJECT_ROOT / output_path
        )

    return (
        input_path.resolve(),
        output_path.resolve(),
    )


def print_result(
    *,
    episode_id: str,
    scene_count: int,
    total_duration: float,
    output_path: Path,
) -> None:
    print("=" * 60)
    print(
        " YouTube Content Factory "
        "- Quiz Timeline Builder"
    )
    print("=" * 60)
    print(f"에피소드: {episode_id}")
    print(f"Timeline 장면 수: {scene_count}")
    print(
        f"전체 길이: {total_duration:.1f}초"
    )
    print("카운트다운: 3 → 2 → 1")
    print("미디어: 기본 색상 배경")
    print(f"출력: {output_path}")
    print("=" * 60)
    print("Quiz Timeline 생성 성공")


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    try:
        input_path, output_path = (
            resolve_paths(
                episode_id=args.episode_id,
                input_value=args.input_path,
                output_value=args.output_path,
            )
        )

        builder = QuizTimelineBuilder()

        timeline = builder.build_from_file(
            scenes_path=input_path,
            output_path=output_path,
        )

        if (
            timeline["episodeId"]
            != args.episode_id
        ):
            raise QuizTimelineBuildError(
                "명령의 episode_id와 생성된 "
                "Timeline의 episodeId가 "
                "일치하지 않습니다."
            )

        print_result(
            episode_id=timeline["episodeId"],
            scene_count=len(
                timeline["scenes"]
            ),
            total_duration=float(
                timeline["totalDuration"]
            ),
            output_path=output_path,
        )

        return 0

    except (
        FileNotFoundError,
        OSError,
        QuizTimelineBuildError,
    ) as error:
        print("=" * 60)
        print(" Quiz Timeline 생성 실패")
        print("=" * 60)
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())