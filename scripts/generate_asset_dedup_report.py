from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.official_assets.asset_dedup import AssetDedupReporter


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_002"
    assets_dir = episode_dir / "assets"

    selection = AssetDedupReporter().generate_from_files(
        sources_path=assets_dir / "sources.json",
        download_report_path=assets_dir / "download_report.md",
        scene_timeline_path=episode_dir / "scene_timeline.json",
        output_dir=assets_dir,
    )

    print(f"Asset selection generated: {assets_dir / 'asset_selection.json'}")
    print(f"Asset dedup report generated: {assets_dir / 'asset_dedup_report.md'}")
    print(f"Downloaded assets: {selection['summary']['downloaded_asset_count']}")
    print(f"Unique assets: {selection['summary']['unique_asset_count']}")
    print(f"Duplicate groups: {selection['summary']['duplicate_group_count']}")
    print(f"Manual-needed scenes: {selection['summary']['manual_needed_count']}")


if __name__ == "__main__":
    main()
