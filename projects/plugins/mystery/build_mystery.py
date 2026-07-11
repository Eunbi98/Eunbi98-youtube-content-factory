from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
PROJECTS_DIR = CURRENT_DIR.parent.parent
DIRECTOR_DIR = PROJECTS_DIR / "director"

for import_path in (
    CURRENT_DIR,
    DIRECTOR_DIR,
):
    resolved = str(import_path)

    if resolved not in sys.path:
        sys.path.insert(
            0,
            resolved,
        )


from mystery_plugin import MysteryPlugin


DEFAULT_EVIDENCE = Path(
    "projects/plugins/mystery/output/"
    "evidence_result.json"
)

DEFAULT_OUTPUT = Path(
    "projects/episodes/ep009/"
    "timeline.json"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mystery Plugin End-to-End 빌드"
        )
    )

    parser.add_argument(
        "--episode-id",
        default="ep009",
    )

    parser.add_argument(
        "--topic",
        default="버뮤다 삼각지대",
    )

    parser.add_argument(
        "--evidence",
        type=Path,
        default=DEFAULT_EVIDENCE,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
    )

    return parser.parse_args()


def main() -> None:
    args = parse_args()

    plugin = MysteryPlugin()

    result = plugin.build(
        episode_id=args.episode_id,
        topic=args.topic,
        evidence_path=args.evidence,
        output_path=args.output,
    )

    print(
        "Mystery Plugin End-to-End 완료"
    )
    print(
        f"Episode: {args.episode_id}"
    )
    print(
        f"주제: {args.topic}"
    )
    print(
        f"Scene 수: {result.scene_count}"
    )
    print(
        "전체 길이: "
        f"{result.total_duration}초"
    )
    print(
        f"출력 경로: {args.output}"
    )


if __name__ == "__main__":
    main()
