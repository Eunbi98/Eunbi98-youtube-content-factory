from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.media import MediaSelector


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    plan = MediaSelector().generate_from_files(
        script_path=episode_dir / "script.json",
        visual_plan_path=episode_dir / "visual_plan.json",
        knowledge_pack_path=episode_dir / "knowledge_pack.json",
        output_dir=episode_dir,
    )

    real_public_count = sum(
        item["media_type"] in {"real_video", "real_image", "official_image"}
        for item in plan
    )
    ai_count = sum(item["media_type"] == "ai_image" for item in plan)
    total = len(plan) or 1

    print(f"Media plan generated: {episode_dir / 'media_plan.json'}")
    print(f"Media plan Markdown generated: {episode_dir / 'media_plan.md'}")
    print(f"Scenes: {len(plan)}")
    print(f"Real/public-first ratio: {real_public_count / total:.1%}")
    print(f"AI image ratio: {ai_count / total:.1%}")


if __name__ == "__main__":
    main()
