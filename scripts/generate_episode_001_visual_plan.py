from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.visual_director import VisualDirector


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    output_path = episode_dir / "visual_plan.json"
    plan = VisualDirector().generate_from_file(
        script_path=episode_dir / "script.json",
        output_path=output_path,
    )

    print(f"Visual plan generated: {output_path}")
    print(f"Scenes: {len(plan)}")


if __name__ == "__main__":
    main()
