from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.scene_timeline import SceneTimelineGenerator
from app.scene_timeline.scene_timeline_types import (
    BGM_ENERGY_LEVELS,
    CAMERA_MOTIONS,
    RECOMMENDED_ASSET_TYPES,
    TRANSITIONS,
)


REQUIRED_KEYS = {
    "scene_id",
    "duration",
    "start_time",
    "end_time",
    "purpose",
    "narration",
    "caption",
    "recommended_asset_type",
    "camera_motion",
    "transition",
    "sfx",
    "bgm_energy",
}


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_002"
    output_json = episode_dir / "scene_timeline.json"
    output_md = episode_dir / "scene_timeline.md"

    timeline = SceneTimelineGenerator().generate_from_files(
        knowledge_pack_path=episode_dir / "knowledge_pack.json",
        story_beats_path=episode_dir / "story_beats.json",
        output_dir=episode_dir,
    )

    assert output_json.exists()
    assert output_md.exists()
    saved = json.loads(output_json.read_text(encoding="utf-8"))
    assert saved == timeline
    assert saved["episode_id"] == "episode_002"
    assert saved["scene_count"] == len(saved["scenes"])
    assert 20 <= saved["total_duration"] <= 25

    previous_end = 0
    for index, scene in enumerate(saved["scenes"], start=1):
        assert REQUIRED_KEYS.issubset(scene)
        assert scene["scene_id"] == f"scene_{index:02d}"
        assert scene["start_time"] == previous_end
        assert scene["end_time"] > scene["start_time"]
        assert scene["duration"] == scene["end_time"] - scene["start_time"]
        assert scene["camera_motion"] in CAMERA_MOTIONS
        assert scene["recommended_asset_type"] in RECOMMENDED_ASSET_TYPES
        assert scene["transition"] in TRANSITIONS
        assert scene["sfx"]
        assert scene["bgm_energy"] in BGM_ENERGY_LEVELS
        assert scene["narration"]
        assert scene["caption"]
        previous_end = scene["end_time"]

    md_text = output_md.read_text(encoding="utf-8")
    assert "Premiere Edit Guide" in md_text
    assert "scene_01" in md_text
    assert "Camera Motion" in md_text

    main_diff = subprocess.run(
        ["git", "diff", "--", "main.py"],
        cwd=PROJECT_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert main_diff.stdout.strip() == ""

    print("scene_timeline_generator_ok")
    print(f"scenes={saved['scene_count']}")
    print(f"duration={saved['total_duration']}")


if __name__ == "__main__":
    main()
