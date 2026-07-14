from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_FILE = Path(__file__).resolve()
QUIZ_DIR = CURRENT_FILE.parent

if str(QUIZ_DIR) not in sys.path:
    sys.path.insert(0, str(QUIZ_DIR))

from source_collector import SourceCollector  # noqa: E402
from source_models import ALLOWED_CATEGORIES, ALLOWED_LEVELS, SourceDataError  # noqa: E402
from source_registry import SourceRegistry  # noqa: E402


DEFAULT_REGISTRY_PATH = QUIZ_DIR / "registry" / "sources.json"
DEFAULT_SOURCE_DATA_DIR = QUIZ_DIR / "source_data"


def parse_categories(raw_value: str) -> set[str]:
    categories = {
        item.strip().lower()
        for item in raw_value.split(",")
        if item.strip()
    }

    if not categories:
        return set(ALLOWED_CATEGORIES)

    invalid = categories - ALLOWED_CATEGORIES

    if invalid:
        raise SourceDataError(
            "지원하지 않는 category: " + ", ".join(sorted(invalid))
        )

    return categories


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="공식 Source Registry에서 검증된 퀴즈 Fact Pool을 생성합니다."
    )
    parser.add_argument(
        "--level",
        required=True,
        choices=sorted(ALLOWED_LEVELS),
        help="elementary, middle, high, current 중 하나",
    )
    parser.add_argument(
        "--categories",
        default=",".join(sorted(ALLOWED_CATEGORIES)),
        help="쉼표로 구분한 category 목록",
    )
    parser.add_argument(
        "--minimum-quality",
        type=float,
        default=75.0,
        help="최소 품질 점수",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Fact Pool 최대 항목 수",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="출력 경로. 생략 시 projects/plugins/quiz/output/fact_pool_<level>.json",
    )
    return parser


def main() -> int:
    args = create_parser().parse_args()

    try:
        categories = parse_categories(args.categories)
        registry = SourceRegistry(DEFAULT_REGISTRY_PATH)
        collector = SourceCollector(
            registry=registry,
            source_data_dir=DEFAULT_SOURCE_DATA_DIR,
        )
        pool = collector.collect(
            level=args.level,
            categories=categories,
            minimum_quality=args.minimum_quality,
            limit=args.limit,
        )

        output_path = args.output

        if output_path is None:
            output_path = QUIZ_DIR / "output" / f"fact_pool_{args.level}.json"

        pool.save(output_path.resolve())

        print("=" * 58)
        print(" Quiz Source Collector 완료")
        print("=" * 58)
        print(f"       난이도: {pool.level}")
        print(f"       Source: {pool.source_count}개")
        print(f"       Fact: {pool.fact_count}개")
        print(f"       품질 기준: {pool.minimum_quality:.1f}")
        print(f"       출력: {output_path.resolve()}")
        return 0

    except SourceDataError as exc:
        print("=" * 58)
        print(" Quiz Source Collector 실패")
        print("=" * 58)
        print(f"       오류: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
