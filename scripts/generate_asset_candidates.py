from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.official_assets import OfficialAssetCollector


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate official asset candidates for an episode.")
    parser.add_argument("--episode", default="episode_001", help="Episode folder name, e.g. episode_002.")
    parser.add_argument("--episode-dir", default=None, help="Explicit episode directory path.")
    parser.add_argument("--live", action="store_true", help="Try live public API lookups where supported.")
    args = parser.parse_args()

    episode_dir = Path(args.episode_dir) if args.episode_dir else PROJECT_ROOT / "episodes" / args.episode

    collector = OfficialAssetCollector(enable_live_lookup=args.live)
    candidates = collector.generate_from_files(
        knowledge_pack_path=episode_dir / "knowledge_pack.json",
        story_beats_path=episode_dir / "story_beats.json",
        script_path=episode_dir / "script.json",
        output_dir=episode_dir,
    )

    scene_keys = sorted(key for key in candidates if key.startswith("scene_"))
    total_candidates = sum(len(candidates[key]) for key in scene_keys if isinstance(candidates[key], list))

    print(f"Asset candidates generated: {episode_dir / 'asset_candidates.json'}")
    print(f"Asset candidates Markdown generated: {episode_dir / 'asset_candidates.md'}")
    print(f"Scenes: {len(scene_keys)}")
    print(f"Candidates: {total_candidates}")


if __name__ == "__main__":
    main()
