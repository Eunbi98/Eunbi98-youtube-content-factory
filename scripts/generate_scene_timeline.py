from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.scene_timeline import SceneTimelineGenerator


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_002"
    timeline = SceneTimelineGenerator().generate_from_files(
        knowledge_pack_path=episode_dir / "knowledge_pack.json",
        story_beats_path=episode_dir / "story_beats.json",
        output_dir=episode_dir,
    )

    print(f"Scene timeline JSON generated: {episode_dir / 'scene_timeline.json'}")
    print(f"Scene timeline Markdown generated: {episode_dir / 'scene_timeline.md'}")
    print(f"Scenes: {timeline['scene_count']}")
    print(f"Duration: {timeline['total_duration']}s")


if __name__ == "__main__":
    main()
