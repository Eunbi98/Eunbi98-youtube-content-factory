from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.narration import Episode001ScriptGenerator, FINAL_NARRATION


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    Episode001ScriptGenerator().generate(episode_dir)

    markdown_path = episode_dir / "script.md"
    json_path = episode_dir / "script.json"

    assert markdown_path.exists()
    assert json_path.exists()

    markdown_text = markdown_path.read_text(encoding="utf-8").rstrip("\n")
    script_data = json.loads(json_path.read_text(encoding="utf-8"))

    assert markdown_text == FINAL_NARRATION
    assert script_data["episode_id"] == "episode_001"
    assert script_data["caption_text"] == FINAL_NARRATION
    assert script_data["narration_lines"] == [
        block.strip()
        for block in FINAL_NARRATION.split("\n\n")
        if block.strip()
    ]

    caption_text = script_data["caption_text"]
    assert "382일" in caption_text
    assert "1~1.5%" in caption_text
    assert "2시간" in caption_text
    assert "382\n일" not in caption_text
    assert "1~\n1.5%" not in caption_text
    assert "2\n시간" not in caption_text

    for filename in [
        "knowledge_pack.json",
        "story_beats.json",
        "beat_sheet.json",
    ]:
        assert filename in script_data["source_inputs"]
        assert (episode_dir / filename).exists()

    print("episode_001_script_ok")


if __name__ == "__main__":
    main()
