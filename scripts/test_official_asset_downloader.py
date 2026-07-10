from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_002"
    assets_dir = episode_dir / "assets"
    manifest_path = assets_dir / "sources.json"
    report_path = assets_dir / "download_report.md"

    assert manifest_path.exists(), "sources.json must exist."
    assert report_path.exists(), "download_report.md must exist."
    assert (assets_dir / "images").exists(), "images directory must exist."
    assert (assets_dir / "videos").exists(), "videos directory must exist."
    assert (assets_dir / "licenses").exists(), "licenses directory must exist."

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["episode_id"] == "episode_002"
    assert "assets" in manifest
    assert "skipped" in manifest

    for asset in manifest["assets"]:
        local_path = Path(asset["local_path"])
        license_path = Path(asset["license_path"])
        assert local_path.exists(), local_path
        assert license_path.exists(), license_path
        assert asset["source"]
        assert asset["original_url"].startswith("https://")
        assert asset["download_url"].startswith("https://")
        assert asset["license"]
        assert asset["media_type"] in {"image", "video"}

    print("official_asset_downloader_ok")
    print(f"downloaded={len(manifest['assets'])}")
    print(f"skipped={len(manifest['skipped'])}")


if __name__ == "__main__":
    main()
