from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.research.knowledge_pack_generator import KnowledgePackGenerator


def main() -> None:
    generator = KnowledgePackGenerator(output_root=PROJECT_ROOT / "episodes")
    result = generator.generate("episode_001")

    print(f"Markdown generated: {result.markdown_path}")
    print(f"JSON generated: {result.json_path}")
    print(f"Sources collected: {result.source_count}")


if __name__ == "__main__":
    main()
