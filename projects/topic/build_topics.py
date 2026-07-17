from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.topic.topic_catalog import CATEGORY_LABELS  # noqa: E402
from projects.topic.topic_finder import (  # noqa: E402
    AutoTopicFinder,
    TopicFinderError,
)


DEFAULT_OUTPUT = Path("projects/output/topics/latest.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="카테고리별 최근 영상 주제 후보를 생성합니다."
    )
    parser.add_argument(
        "--category",
        required=True,
        choices=tuple(CATEGORY_LABELS),
        help="주제 카테고리",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="생성할 후보 개수 (기본값: 10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"결과 JSON 경로 (기본값: {DEFAULT_OUTPUT})",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = AutoTopicFinder().find(
            category=args.category,
            limit=args.limit,
        )
    except TopicFinderError as exc:
        print(f"[실패] {exc}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Auto Topic Finder 완료")
    print(f"카테고리: {CATEGORY_LABELS[result.category]}")
    print(f"수집 모드: {result.mode}")
    for candidate in result.candidates:
        print(f"{candidate.rank:>2}. [{candidate.score:>4.1f}] {candidate.topic}")
    print(f"출력: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
