from __future__ import annotations

from pathlib import Path
from typing import Callable

from build_timeline import (
    build_ep008_story,
    build_ep010_story,
    build_ep011_story,
    build_ep012_story,
    build_ep013_story,
)
from factory_core import FactoryBuildResult, FactoryCore
from story_graph import Story
from timeline_schema import save_timeline


class DirectorError(RuntimeError):
    """Director 처리 실패."""


STORY_BUILDERS: dict[str, Callable[[], Story]] = {
    "ep008": build_ep008_story,
    "ep010": build_ep010_story,
    "ep011": build_ep011_story,
    "ep012": build_ep012_story,
    "ep013": build_ep013_story,
}


class Director:
    def build(
        self,
        *,
        episode_id: str,
        output_path: Path,
    ) -> FactoryBuildResult:
        normalized_episode_id = episode_id.lower()

        story_builder = STORY_BUILDERS.get(
            normalized_episode_id
        )

        if story_builder is None:
            supported = ", ".join(
                sorted(STORY_BUILDERS)
            )
            raise DirectorError(
                "지원하지 않는 에피소드입니다. "
                f"요청: {episode_id}, 지원: {supported}"
            )

        story = story_builder()

        if (
            story.episode_id.lower()
            != normalized_episode_id
        ):
            raise DirectorError(
                "Story episode_id가 요청값과 다릅니다. "
                f"Story: {story.episode_id}, "
                f"요청: {episode_id}"
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
