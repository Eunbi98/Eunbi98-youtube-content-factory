from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
QUIZ_DIR = CURRENT_FILE.parent

if str(QUIZ_DIR) not in sys.path:
    sys.path.insert(0, str(QUIZ_DIR))

from fact_validator import (  # noqa: E402
    FactValidationError,
    QuestionPoolValidator,
)


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Quiz Question Pool의 출처, 중복, 최신성, 구조를 검증합니다."
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
        help="생략 시 output/question_pool_<level>.json을 사용합니다.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="생략 시 output/question_pool_<level>_validated.json에 저장합니다.",
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help="생략 시 output/validation_report_<level>.json에 저장합니다.",
    )
    parser.add_argument(
        "--minimum-validation-score",
        type=float,
        default=75.0,
    )
    parser.add_argument(
        "--reject-warnings",
        action="store_true",
        help="경고가 하나라도 있는 문제도 제외합니다.",
    )
    return parser


def main() -> int:
    args = create_parser().parse_args()
    input_path = args.input or (
        QUIZ_DIR / "output" / f"question_pool_{args.level}.json"
    )
    output_path = args.output or (
        QUIZ_DIR / "output" / f"question_pool_{args.level}_validated.json"
    )
    report_path = args.report or (
        QUIZ_DIR / "output" / f"validation_report_{args.level}.json"
    )

    try:
        report = QuestionPoolValidator().validate_file(
            input_path=input_path,
            output_path=output_path,
            report_path=report_path,
            minimum_validation_score=args.minimum_validation_score,
            reject_warnings=args.reject_warnings,
        )
        print("=" * 58)
        print(" Quiz Fact Validator 완료")
        print("=" * 58)
        print(f"       입력: {report['input_count']}개")
        print(f"       통과: {report['accepted_count']}개")
        print(f"       제외: {report['rejected_count']}개")
        print(f"       출력: {output_path.resolve()}")
        print(f"       보고서: {report_path.resolve()}")
        return 0
    except FactValidationError as exc:
        print("=" * 58)
        print(" Quiz Fact Validator 실패")
        print("=" * 58)
        print(f"       오류: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
