from __future__ import annotations

import json
import re
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.beat_sheet import Episode001BeatSheetGenerator


REQUIRED_BEAT_KEYS = {
    "start_time",
    "end_time",
    "purpose",
    "narration_intent",
    "caption_text",
    "visual_direction",
    "emotion",
    "transition_note",
}


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    generator = Episode001BeatSheetGenerator()
    generator.generate_from_files(
        knowledge_pack_path=episode_dir / "knowledge_pack.json",
        story_beats_path=episode_dir / "story_beats.json",
        output_dir=episode_dir,
    )

    json_path = episode_dir / "beat_sheet.json"
    markdown_path = episode_dir / "beat_sheet.md"

    assert json_path.exists()
    assert markdown_path.exists()

    beat_sheet = json.loads(json_path.read_text(encoding="utf-8"))
    beats = beat_sheet["beats"]

    assert beat_sheet["episode_id"] == "episode_001"
    assert beat_sheet["duration_seconds"] <= 60
    assert len(beats) == 8
    assert beats[0]["start_time"] == 0
    assert beats[-1]["end_time"] == 60

    expected_ranges = [
        (0, 3),
        (3, 8),
        (8, 14),
        (14, 24),
        (24, 36),
        (36, 46),
        (46, 55),
        (55, 60),
    ]
    actual_ranges = [
        (beat["start_time"], beat["end_time"])
        for beat in beats
    ]
    assert actual_ranges == expected_ranges

    for beat in beats:
        assert REQUIRED_BEAT_KEYS.issubset(beat)
        assert beat["end_time"] > beat["start_time"]
        sentence_end_count = len(
            re.findall(r"(?<!\d)[.?!](?!\d)", beat["caption_text"])
        )
        assert sentence_end_count <= 2

        caption_lines = beat["caption_text"].splitlines()
        assert 1 <= len(caption_lines) <= 2
        for line in caption_lines:
            assert len(line) <= 32

    caption_blob = "\n".join(beat["caption_text"] for beat in beats)
    assert "382일" in caption_blob
    assert "1~1.5%" in caption_blob
    assert "Scott Kelly" in caption_blob
    assert "Frank Rubio" in caption_blob
    assert "340일" in caption_blob
    assert "371일" in caption_blob
    assert "Scott\nKelly" not in caption_blob
    assert "Frank\nRubio" not in caption_blob
    assert "1~\n1.5%" not in caption_blob
    assert "371\n일" not in caption_blob
    assert beats[-1]["caption_text"].endswith("화성에서는 더 심해질까요?")

    print("episode_001_beat_sheet_ok")


if __name__ == "__main__":
    main()
