from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.narration import Episode001ScriptGenerator


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    result = Episode001ScriptGenerator().generate(episode_dir)

    print(f"Script Markdown generated: {result.markdown_path}")
    print(f"Script JSON generated: {result.json_path}")
    print(f"Narration lines: {result.line_count}")


if __name__ == "__main__":
    main()
