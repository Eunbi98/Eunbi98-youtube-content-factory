from __future__ import annotations

import argparse
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.official_assets import OfficialAssetDownloader


def main() -> None:
    parser = argparse.ArgumentParser(description="Download selected official asset candidates.")
    parser.add_argument("--episode", default="episode_002", help="Episode folder name, e.g. episode_002.")
    parser.add_argument("--episode-dir", default=None, help="Explicit episode directory path.")
    parser.add_argument("--max-assets-per-scene", type=int, default=2)
    parser.add_argument("--max-mb", type=int, default=30)
    args = parser.parse_args()

    episode_dir = Path(args.episode_dir) if args.episode_dir else PROJECT_ROOT / "episodes" / args.episode
    downloader = OfficialAssetDownloader(
        max_assets_per_scene=args.max_assets_per_scene,
        max_bytes=args.max_mb * 1024 * 1024,
    )
    manifest = downloader.download_from_file(
        asset_candidates_path=episode_dir / "asset_candidates.json",
        output_dir=episode_dir / "assets",
    )

    assets = manifest.get("assets", [])
    skipped = manifest.get("skipped", [])
    image_count = sum(1 for asset in assets if asset.get("media_type") == "image")
    video_count = sum(1 for asset in assets if asset.get("media_type") == "video")

    print(f"Assets directory: {episode_dir / 'assets'}")
    print(f"Downloaded assets: {len(assets)}")
    print(f"Images: {image_count}")
    print(f"Videos: {video_count}")
    print(f"Skipped candidates: {len(skipped)}")
    print(f"Source manifest: {episode_dir / 'assets' / 'sources.json'}")
    print(f"Download report: {episode_dir / 'assets' / 'download_report.md'}")


if __name__ == "__main__":
    main()
