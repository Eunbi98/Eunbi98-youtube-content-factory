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

from projects.plugins.quiz.quiz_schema import (  # noqa: E402
    QuizValidationError,
)
from projects.plugins.quiz.quiz_story_builder import (  # noqa: E402
    QuizStoryBuilder,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "주관식 퀴즈 입력 JSON을 검증하고 "
            "에피소드 quiz_story.json을 생성합니다."
        )
    )

    parser.add_argument(
        "--episode-id",
        default="ep010",
        help="생성할 에피소드 ID",
    )
    parser.add_argument(
        "--input",
        dest="input_path",
        default=None,
        help="퀴즈 입력 JSON 경로",
    )
    parser.add_argument(
        "--output",
        dest="output_path",
        default=None,
        help="생성할 quiz_story.json 경로",
    )

    return parser


def resolve_paths(
    episode_id: str,
    input_value: str | None,
    output_value: str | None,
) -> tuple[Path, Path]:
    normalized_episode_id = episode_id.strip()

    if not normalized_episode_id:
        raise QuizValidationError(
            "episode_id는 비어 있을 수 없습니다."
        )

    input_path = (
        Path(input_value)
        if input_value
        else (
            QUIZ_DIR
            / "input"
            / f"{normalized_episode_id}_quiz.json"
        )
    )

    output_path = (
        Path(output_value)
        if output_value
        else (
            PROJECT_ROOT
            / "projects"
            / "episodes"
            / normalized_episode_id
            / "quiz_story.json"
        )
    )

    if not input_path.is_absolute():
        input_path = PROJECT_ROOT / input_path

    if not output_path.is_absolute():
        output_path = PROJECT_ROOT / output_path

    return (
        input_path.resolve(),
        output_path.resolve(),
    )


def print_result(
    episode_id: str,
    title: str,
    question_count: int,
    output_path: Path,
) -> None:
    print("=" * 58)
    print(" YouTube Content Factory - Quiz Story Builder")
    print("=" * 58)
    print(f"에피소드: {episode_id}")
    print(f"제목: {title}")
    print(f"문제 수: {question_count}")
    print("형식: 주관식")
    print("카운트다운: 3초")
    print("문제 TTS: 사용")
    print("정답 TTS: 사용")
    print("카운트다운 TTS: 미사용")
    print("해설: 미사용")
    print(f"출력: {output_path}")
    print("=" * 58)
    print("Quiz Story 생성 성공")


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    try:
        input_path, output_path = resolve_paths(
            episode_id=args.episode_id,
            input_value=args.input_path,
            output_value=args.output_path,
        )

        builder = QuizStoryBuilder()
        episode = builder.build(
            source_path=input_path,
            output_path=output_path,
        )

        if episode.episode_id != args.episode_id:
            raise QuizValidationError(
                "명령의 episode_id와 입력 JSON의 "
                "episode_id가 일치하지 않습니다. "
                f"명령: {args.episode_id}, "
                f"JSON: {episode.episode_id}"
            )

        print_result(
            episode_id=episode.episode_id,
            title=episode.title,
            question_count=episode.question_count,
            output_path=output_path,
        )

        return 0

    except (
        FileNotFoundError,
        OSError,
        QuizValidationError,
    ) as error:
        print("=" * 58)
        print(" Quiz Story 생성 실패")
        print("=" * 58)
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())