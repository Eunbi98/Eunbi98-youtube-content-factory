from __future__ import annotations

import argparse
import json
from pathlib import Path

from evidence_collector import (
    EvidenceCollector,
)
from evidence_schema import RawEvidence


DEFAULT_TOPIC = "버뮤다 삼각지대"

DEFAULT_INPUT = Path(
    "projects/plugins/mystery/input/"
    "raw_evidence.json"
)

DEFAULT_OUTPUT = Path(
    "projects/plugins/mystery/output/"
    "evidence_result.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mystery Plugin Evidence 정규화"
        )
    )

    parser.add_argument(
        "--topic",
        default=DEFAULT_TOPIC,
    )

    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def load_raw_items(
    path: Path,
) -> list[RawEvidence]:
    if not path.exists():
        raise FileNotFoundError(
            "입력 파일이 없습니다: "
            f"{path}"
        )

    with path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(
            "입력 JSON의 최상위 값은 "
            "배열이어야 합니다."
        )

    return [
        RawEvidence(**item)
        for item in data
    ]


def main() -> None:
    args = parse_args()

    raw_items = load_raw_items(
        args.input
    )

    collector = EvidenceCollector()

    result = collector.collect(
        topic=args.topic,
        raw_items=raw_items,
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
        "Mystery Evidence 처리 완료"
    )
    print(
        f"주제: {result.topic}"
    )
    print(
        f"채택 근거: {len(result.items)}"
    )
    print(
        f"중복 제거: {result.duplicate_count}"
    )
    print(
        f"거부 항목: {result.rejected_count}"
    )
    print(
        f"출력 경로: {args.output}"
    )


if __name__ == "__main__":
    main()
