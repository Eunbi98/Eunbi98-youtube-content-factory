from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
QUIZ_DIR = CURRENT_FILE.parent
PROJECT_ROOT = CURRENT_FILE.parents[3]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(PROJECT_ROOT),
    )

from projects.plugins.quiz.quiz_scene_builder import (  # noqa: E402
    QuizSceneBuildError,
    QuizSceneBuilder,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "quiz_story.json을 읽어서 "
            "quiz_scenes.json을 생성합니다."
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
        help="quiz_story.json 경로",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default=None,
        help="quiz_scenes.json 출력 경로",
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
        raise QuizSceneBuildError(
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
        else episode_dir / "quiz_story.json"
    )
    output_path = (
        Path(output_value)
        if output_value
        else episode_dir / "quiz_scenes.json"
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
    print("=" * 58)
    print(
        " YouTube Content Factory "
        "- Quiz Scene Builder"
    )
    print("=" * 58)
    print(f"에피소드: {episode_id}")
    print(f"장면 수: {scene_count}")
    print(
        f"예상 영상 길이: "
        f"{total_duration:.1f}초"
    )
    print("구조: 문제 → 3초 → 정답")
    print("문제 TTS: 사용")
    print("카운트다운: 효과음")
    print("정답 TTS: 사용")
    print("해설: 미사용")
    print(f"출력: {output_path}")
    print("=" * 58)
    print("Quiz Scene 생성 성공")


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

        builder = QuizSceneBuilder()
        collection = builder.build_from_file(
            story_path=input_path,
            output_path=output_path,
        )

        if (
            collection.episode_id
            != args.episode_id
        ):
            raise QuizSceneBuildError(
                "명령의 episode_id와 "
                "Quiz Story의 episode_id가 "
                "일치하지 않습니다."
            )

        print_result(
            episode_id=collection.episode_id,
            scene_count=collection.scene_count,
            total_duration=(
                collection.total_duration
            ),
            output_path=output_path,
        )

        return 0

    except (
        FileNotFoundError,
        OSError,
        QuizSceneBuildError,
    ) as error:
        print("=" * 58)
        print(" Quiz Scene 생성 실패")
        print("=" * 58)
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())