from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.official_assets.asset_dedup import AssetDedupReporter


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_002"
    assets_dir = episode_dir / "assets"
    selection_path = assets_dir / "asset_selection.json"
    report_path = assets_dir / "asset_dedup_report.md"

    selection = AssetDedupReporter().generate_from_files(
        sources_path=assets_dir / "sources.json",
        download_report_path=assets_dir / "download_report.md",
        scene_timeline_path=episode_dir / "scene_timeline.json",
        output_dir=assets_dir,
    )

    assert selection_path.exists()
    assert report_path.exists()
    saved = json.loads(selection_path.read_text(encoding="utf-8"))
    timeline = json.loads((episode_dir / "scene_timeline.json").read_text(encoding="utf-8"))
    assert saved == selection
    assert len(saved["scenes"]) == len(timeline["scenes"])
    assert saved["summary"]["downloaded_asset_count"] >= saved["summary"]["unique_asset_count"]
    assert saved["summary"]["duplicate_group_count"] >= 1

    for scene in saved["scenes"]:
        assert "scene_id" in scene
        assert "selected_asset" in scene
        assert "manual_needed" in scene
        assert isinstance(scene["manual_needed"], bool)
        assert scene["search_queries"]
        if scene["selected_asset"]:
            assert scene["selected_asset"]["license_path"]
            assert scene["selected_asset"]["sha256"]

    for group in saved["duplicate_groups"]:
        assert group["representative_asset"]["license_path"]
        assert len(group["duplicate_assets"]) >= 1

    main_diff = subprocess.run(
        ["git", "diff", "--", "main.py"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert main_diff.stdout.strip() == ""

    print("asset_dedup_report_ok")
    print(f"unique_assets={saved['summary']['unique_asset_count']}")
    print(f"manual_needed={saved['summary']['manual_needed_count']}")


if __name__ == "__main__":
    main()
