from __future__ import annotations

import argparse
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent

PROJECTS_DIR = (
    CURRENT_DIR.parent.parent
)

DIRECTOR_DIR = (
    PROJECTS_DIR / "director"
)

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


from factory_core import FactoryCore
from mystery_plugin import MysteryPlugin
from timeline_schema import save_timeline


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
            "Mystery Story와 Timeline 자동 생성"
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

    story = plugin.generate(
        episode_id=args.episode_id,
        topic=args.topic,
        evidence_path=args.evidence,
    )

    factory = FactoryCore()

    result = factory.build_with_result(
        story
    )

    save_timeline(
        result.timeline,
        args.output,
    )

    print(
        "Mystery Plugin Story 생성 완료"
    )
    print(
        f"주제: {story.title}"
    )
    print(
        f"Beat 수: {len(story.beats)}"
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
