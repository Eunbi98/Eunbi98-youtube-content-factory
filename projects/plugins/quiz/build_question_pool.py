from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
QUIZ_DIR = CURRENT_FILE.parent

if str(QUIZ_DIR) not in sys.path:
    sys.path.insert(0, str(QUIZ_DIR))

from question_generator import QuestionGenerator  # noqa: E402
from question_models import QuestionDataError  # noqa: E402


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fact Pool에서 검증 가능한 Quiz Question Pool을 생성합니다."
    )
    parser.add_argument(
        "--level",
        required=True,
        choices=("elementary", "middle", "high", "current"),
    )
    parser.add_argument(
        "--fact-pool",
        type=Path,
        default=None,
        help="생략 시 output/fact_pool_<level>.json을 사용합니다.",
    )
    parser.add_argument(
        "--minimum-quality",
        type=float,
        default=70.0,
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="생략 시 output/question_pool_<level>.json에 저장합니다.",
    )
    return parser


def main() -> int:
    args = create_parser().parse_args()

    fact_pool_path = args.fact_pool

    if fact_pool_path is None:
        fact_pool_path = QUIZ_DIR / "output" / f"fact_pool_{args.level}.json"

    output_path = args.output

    if output_path is None:
        output_path = QUIZ_DIR / "output" / f"question_pool_{args.level}.json"

    try:
        pool = QuestionGenerator().generate_from_file(
            fact_pool_path=fact_pool_path,
            minimum_quality=args.minimum_quality,
            limit=args.limit,
        )
        pool.save(output_path)

        print("=" * 58)
        print(" Quiz Question Generator 완료")
        print("=" * 58)
        print(f"       난이도: {pool.level}")
        print(f"       문제: {pool.question_count}개")
        print(f"       품질 기준: {pool.minimum_quality:.1f}")
        print(f"       입력: {fact_pool_path.resolve()}")
        print(f"       출력: {output_path.resolve()}")
        return 0

    except QuestionDataError as exc:
        print("=" * 58)
        print(" Quiz Question Generator 실패")
        print("=" * 58)
        print(f"       오류: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
