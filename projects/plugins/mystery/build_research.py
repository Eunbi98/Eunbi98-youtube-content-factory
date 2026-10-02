from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_engine import (
    MysteryResearchEngine,
)


DEFAULT_TOPIC = "버뮤다 삼각지대"

DEFAULT_OUTPUT = Path(
    "projects/plugins/mystery/output/"
    "research_result.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mystery Plugin Research 계획 생성"
        )
    )

    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
        help=(
            "조사할 주제 "
            f"(기본값: {DEFAULT_TOPIC})"
        ),
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=(
            "결과 JSON 저장 경로"
        ),
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    engine = MysteryResearchEngine()

    result = engine.build(
        args.topic
    )

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with args.output.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            result.to_dict(),
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")

    print(
        "Mystery Research 계획 생성 완료"
    )
    print(
        f"주제: {result.normalized_topic}"
    )
    print(
        "검색 키워드 수: "
        f"{len(result.search_keywords)}"
    )
    print(
        "조사 질문 수: "
        f"{len(result.research_questions)}"
    )
    print(
        f"출력 경로: {args.output}"
    )


if __name__ == "__main__":
    main()
