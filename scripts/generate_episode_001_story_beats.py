from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.story_beats import StoryBeatGenerator


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    generator = StoryBeatGenerator()
    result = generator.generate_from_file(
        input_path=episode_dir / "knowledge_pack.json",
        output_path=episode_dir / "story_beats.json",
    )

    print(f"Story beats generated: {result.output_path}")


if __name__ == "__main__":
    main()
