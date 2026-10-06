from __future__ import annotations

import argparse
import json
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

from projects.plugins.quiz.question_engine import (  # noqa: E402
    ALLOWED_CATEGORIES,
    QuestionBank,
    QuestionEngine,
    QuestionEngineError,
    load_excluded_hashes,
)


QUESTION_BANK_DIR = (
    QUIZ_DIR
    / "question_bank"
)

QUIZ_INPUT_DIR = (
    QUIZ_DIR
    / "input"
)

EPISODES_DIR = (
    PROJECT_ROOT
    / "projects"
    / "episodes"
)


def normalize_episode_id(
    raw_value: str,
) -> str:
    value = raw_value.strip().lower()

    if value.startswith("ep"):
        number_text = value[2:]
    else:
        number_text = value

    if not number_text.isdigit():
        raise QuestionEngineError(
            "에피소드 ID 형식이 올바르지 않습니다. "
            "예: ep010"
        )

    return f"ep{int(number_text):03d}"


def parse_categories(
    raw_value: str,
) -> set[str]:
    categories = {
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    }

    if not categories:
        return set(ALLOWED_CATEGORIES)

    invalid = (
        categories
        - ALLOWED_CATEGORIES
    )

    if invalid:
        raise QuestionEngineError(
            "지원하지 않는 카테고리: "
            + ", ".join(sorted(invalid))
        )

    return categories


def write_json_atomic(
    path: Path,
    data: dict,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = path.with_suffix(
        path.suffix + ".tmp"
    )

    with temporary_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")

    temporary_path.replace(path)


def find_previous_selection_files(
    current_episode_id: str,
) -> list[Path]:
    current_number = int(
        current_episode_id[2:]
    )

    results: list[Path] = []

    for episode_dir in sorted(
        EPISODES_DIR.glob("ep*")
    ):
        name = episode_dir.name.lower()

        if (
            not name.startswith("ep")
            or not name[2:].isdigit()
        ):
            continue

        episode_number = int(name[2:])

        if episode_number >= current_number:
            continue

        selection_path = (
            episode_dir
            / "question_selection.json"
        )

        if selection_path.exists():
            results.append(selection_path)

    return results


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Question Bank에서 퀴즈 문제를 "
            "검증하고 자동 선택합니다."
        )
    )

    parser.add_argument(
        "--episode-id",
        default="ep010",
        help="에피소드 ID",
    )
    parser.add_argument(
        "--title",
        default="알고도 틀리는 상식 퀴즈 5문제",
        help="퀴즈 영상 제목",
    )
    parser.add_argument(
        "--count",
        type=int,
        default=5,
        help="선택할 문제 수",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=10,
        help="재현 가능한 선택용 seed",
    )
    parser.add_argument(
        "--categories",
        default=(
            "science,history,geography,"
            "language,society,culture,general"
        ),
        help=(
            "쉼표로 구분한 카테고리 목록"
        ),
    )
    parser.add_argument(
        "--minimum-quality",
        type=float,
        default=75.0,
        help="최소 품질 점수",
    )
    parser.add_argument(
        "--allow-previous",
        action="store_true",
        help=(
            "이전 에피소드에 사용한 문제도 "
            "선택할 수 있게 합니다."
        ),
    )

    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    try:
        episode_id = normalize_episode_id(
            args.episode_id
        )

        categories = parse_categories(
            args.categories
        )

        if args.count <= 0:
            raise QuestionEngineError(
                "--count는 1 이상이어야 합니다."
            )

        if not 0 <= args.minimum_quality <= 100:
            raise QuestionEngineError(
                "--minimum-quality는 "
                "0~100 사이여야 합니다."
            )

        bank = QuestionBank(
            max_question_lines=2,
            max_chars_per_line=15,
        )

        candidates = bank.load_directory(
            QUESTION_BANK_DIR
        )

        if args.allow_previous:
            excluded_hashes: set[str] = set()
        else:
            previous_files = (
                find_previous_selection_files(
                    episode_id
                )
            )
            excluded_hashes = (
                load_excluded_hashes(
                    previous_files
                )
            )

        engine = QuestionEngine(
            minimum_quality_score=(
                args.minimum_quality
            )
        )

        result = engine.select(
            episode_id=episode_id,
            title=args.title.strip(),
            candidates=candidates,
            count=args.count,
            seed=args.seed,
            categories=categories,
            excluded_hashes=excluded_hashes,
        )

        quiz_input_path = (
            QUIZ_INPUT_DIR
            / f"{episode_id}_quiz.json"
        )

        selection_output_path = (
            EPISODES_DIR
            / episode_id
            / "question_selection.json"
        )

        write_json_atomic(
            quiz_input_path,
            result.to_quiz_input_dict(),
        )

        write_json_atomic(
            selection_output_path,
            result.to_dict(),
        )

        print("=" * 64)
        print(
            " YouTube Content Factory "
            "- Question Engine"
        )
        print("=" * 64)
        print(f"에피소드: {episode_id}")
        print(f"제목: {result.title}")
        print(
            f"Question Bank 문제 수: "
            f"{len(candidates)}"
        )
        print(
            f"선택 문제 수: "
            f"{result.selected_count}"
        )
        print(
            f"최소 품질 점수: "
            f"{args.minimum_quality:.1f}"
        )
        print(f"선택 Seed: {args.seed}")
        print("-" * 64)

        for index, question in enumerate(
            result.selected_questions,
            start=1,
        ):
            print(
                f"{index}. "
                f"[{question.category}/"
                f"{question.difficulty}] "
                f"{question.question}"
            )
            print(
                f"   정답: {question.answer}"
            )
            print(
                f"   품질: "
                f"{question.quality_score:.2f}"
            )

        print("-" * 64)
        print(
            f"Quiz 입력: "
            f"{quiz_input_path}"
        )
        print(
            f"선택 기록: "
            f"{selection_output_path}"
        )
        print("=" * 64)
        print("Question Engine 실행 성공")

        return 0

    except (
        FileNotFoundError,
        OSError,
        QuestionEngineError,
    ) as error:
        print("=" * 64)
        print(" Question Engine 실행 실패")
        print("=" * 64)
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())