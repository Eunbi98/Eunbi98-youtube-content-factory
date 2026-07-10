from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.official_assets import OfficialAssetCollector
from app.official_assets.asset_types import SOURCE_PRIORITY, TRUST_SCORE_BY_SOURCE


REQUIRED_KEYS = {
    "title",
    "source",
    "url",
    "license",
    "media_type",
    "keywords",
    "trust_score",
}


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    output_json = episode_dir / "asset_candidates.json"
    output_md = episode_dir / "asset_candidates.md"

    candidates = OfficialAssetCollector().generate_from_files(
        knowledge_pack_path=episode_dir / "knowledge_pack.json",
        story_beats_path=episode_dir / "story_beats.json",
        script_path=episode_dir / "script.json",
        output_dir=episode_dir,
    )

    assert output_json.exists()
    assert output_md.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    script = json.loads((episode_dir / "script.json").read_text(encoding="utf-8"))
    assert saved == candidates

    scene_keys = sorted(key for key in saved if re.fullmatch(r"scene_\d+", key))
    assert len(scene_keys) == len(script["narration_lines"])
    assert saved["source_priority"] == SOURCE_PRIORITY

    for scene_key in scene_keys:
        scene_candidates = saved[scene_key]
        assert isinstance(scene_candidates, list)
        assert len(scene_candidates) >= 3

        media_types = {candidate["media_type"] for candidate in scene_candidates}
        assert {"image", "video"}.issubset(media_types)

        for candidate in scene_candidates:
            assert REQUIRED_KEYS.issubset(candidate)
            assert candidate["source"] in TRUST_SCORE_BY_SOURCE
            assert candidate["trust_score"] == TRUST_SCORE_BY_SOURCE[candidate["source"]]
            assert candidate["media_type"] in {"image", "video"}
            assert candidate["url"].startswith("https://")
            assert candidate["keywords"]

    md_text = output_md.read_text(encoding="utf-8")
    assert "## scene_01" in md_text
    assert "추천 1" in md_text

    main_diff = subprocess.run(
        ["git", "diff", "--", "main.py"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert main_diff.stdout.strip() == ""

    print("asset_collector_ok")
    print(f"scenes={len(scene_keys)}")
    print(f"candidates_per_scene={len(saved[scene_keys[0]])}")


if __name__ == "__main__":
    main()
