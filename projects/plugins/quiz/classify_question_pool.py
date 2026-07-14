from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
QUIZ_DIR = CURRENT_FILE.parent

if str(QUIZ_DIR) not in sys.path:
    sys.path.insert(0, str(QUIZ_DIR))

from difficulty_classifier import (  # noqa: E402
    DifficultyClassificationError,
    DifficultyClassifier,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="검증된 Quiz Question Pool의 난이도를 자동 분류합니다."
    )
    parser.add_argument(
        "--level",
        required=True,
        choices=("elementary", "middle", "high", "current"),
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=None,
        help="생략 시 output/question_pool_<level>_validated.json을 사용합니다.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="생략 시 output/question_pool_<level>_classified.json에 저장합니다.",
    )
    parser.add_argument(
        "--minimum-confidence",
        type=float,
        default=0.45,
    )
    parser.add_argument(
        "--enforce-declared-level",
        action="store_true",
        help="자동 분류 결과와 선언 난이도가 다른 문제를 미통과 처리합니다.",
    )
    return parser


def main() -> int:
    args = create_parser().parse_args()
    input_path = args.input or (
        QUIZ_DIR / "output" / f"question_pool_{args.level}_validated.json"
    )
    output_path = args.output or (
        QUIZ_DIR / "output" / f"question_pool_{args.level}_classified.json"
    )

    try:
        report = DifficultyClassifier().classify_file(
            input_path=input_path,
            output_path=output_path,
            minimum_confidence=args.minimum_confidence,
            enforce_declared_level=args.enforce_declared_level,
        )
        print("=" * 58)
        print(" Quiz Difficulty Classifier 완료")
        print("=" * 58)
        print(f"       입력: {report['input_count']}개")
        print(f"       분류: {report['classified_count']}개")
        print(f"       난이도 불일치: {report['mismatch_count']}개")
        print(f"       낮은 확신도: {report['low_confidence_count']}개")
        print(f"       출력: {report['output']}")
        return 0
    except DifficultyClassificationError as exc:
        print("=" * 58)
        print(" Quiz Difficulty Classifier 실패")
        print("=" * 58)
        print(f"       오류: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
