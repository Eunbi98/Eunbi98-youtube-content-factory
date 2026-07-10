from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.beat_sheet import Episode001BeatSheetGenerator


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    generator = Episode001BeatSheetGenerator()
    result = generator.generate_from_files(
        knowledge_pack_path=episode_dir / "knowledge_pack.json",
        story_beats_path=episode_dir / "story_beats.json",
        output_dir=episode_dir,
    )

    print(f"Beat sheet JSON generated: {result.json_path}")
    print(f"Beat sheet Markdown generated: {result.markdown_path}")
    print(f"Duration: {result.duration_seconds}s")


if __name__ == "__main__":
    main()
