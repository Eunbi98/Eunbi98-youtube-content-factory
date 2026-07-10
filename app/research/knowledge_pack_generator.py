from __future__ import annotations

import json
from pathlib import Path

from app.research.episode_001_pack import build_episode_001_knowledge_pack
from app.research.knowledge_pack_types import KnowledgePack, KnowledgePackResult


class KnowledgePackGenerator:
    def __init__(self, output_root: Path | str = "episodes") -> None:
        self.output_root = Path(output_root)

    def generate(self, episode_id: str = "episode_001") -> KnowledgePackResult:
        if episode_id != "episode_001":
            raise ValueError("Only episode_001 is supported for now.")

        pack = build_episode_001_knowledge_pack()
        episode_dir = self.output_root / pack.episode_id
        episode_dir.mkdir(parents=True, exist_ok=True)

        markdown_path = episode_dir / "knowledge_pack.md"
        json_path = episode_dir / "knowledge_pack.json"

        markdown_path.write_text(
            self._render_markdown(pack),
            encoding="utf-8",
        )
        json_path.write_text(
            json.dumps(pack.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return KnowledgePackResult(
            episode_id=pack.episode_id,
            output_path=markdown_path,
            markdown_path=markdown_path,
            json_path=json_path,
            source_count=len(pack.sources),
        )

    def _render_markdown(self, pack: KnowledgePack) -> str:
        sections = [
            "# Main Question",
            "",
            pack.main_question,
            "",
            "# Common Misconceptions",
            "",
            self._render_list(pack.common_misconceptions),
            "",
            "# Verified Facts",
            "",
            self._render_list(pack.verified_facts),
            "",
            "# Surprising Facts",
            "",
            self._render_list(pack.surprising_facts),
            "",
            "# Timeline",
            "",
            self._render_list(pack.timeline),
            "",
            "# Story Materials",
            "",
            self._render_list(pack.story_materials),
            "",
            "# Visual Ideas",
            "",
            self._render_list(pack.visual_ideas),
            "",
            "# Sources",
            "",
            self._render_sources(pack),
            "",
        ]

        return "\n".join(sections)

    def _render_list(self, items: list[str]) -> str:
        return "\n".join(f"- {item}" for item in items)

    def _render_sources(self, pack: KnowledgePack) -> str:
        lines: list[str] = []

        for index, source in enumerate(pack.sources, start=1):
            lines.append(
                f"{index}. [{source.title}]({source.url}) - "
                f"{source.publisher} / {source.source_type}"
            )
            for note in source.notes:
                lines.append(f"   - {note}")

        return "\n".join(lines)
