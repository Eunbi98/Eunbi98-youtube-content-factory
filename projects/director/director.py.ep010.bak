from __future__ import annotations

from pathlib import Path

from build_timeline import build_ep008_story
from factory_core import FactoryBuildResult, FactoryCore
from timeline_schema import save_timeline


class DirectorError(RuntimeError):
    """Director 처리 실패."""


class Director:
    def build(
        self,
        *,
        episode_id: str,
        output_path: Path,
    ) -> FactoryBuildResult:
        if episode_id != "ep008":
            raise DirectorError(
                "현재 Story 생성기는 ep008만 지원합니다. "
                f"요청: {episode_id}"
            )

        story = build_ep008_story()

        if story.episode_id.lower() != episode_id:
            raise DirectorError(
                "Story episode_id가 요청값과 다릅니다. "
                f"Story: {story.episode_id}, 요청: {episode_id}"
            )

        result = FactoryCore().build_with_result(
            story
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        save_timeline(
            result.timeline,
            str(output_path),
        )

        if not output_path.exists():
            raise DirectorError(
                "timeline.json 저장에 실패했습니다: "
                f"{output_path}"
            )

        return result
