from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from story_graph import Story
from story_optimizer import StoryOptimizer
from story_planner import (
    MysteryStoryPlan,
    MysteryStoryPlanner,
)


class MysteryPlugin:
    """
    Mystery 장르 콘텐츠 생성 진입점입니다.

    generate():
        Evidence JSON을 Story Graph로 변환합니다.

    build():
        Story 생성부터 Factory Core Timeline 생성 및 저장까지
        한 번에 실행합니다.
    """

    def __init__(
        self,
        *,
        story_planner: MysteryStoryPlanner | None = None,
        story_optimizer: StoryOptimizer | None = None,
    ) -> None:
        self._story_planner = (
            story_planner
            or MysteryStoryPlanner()
        )

        self._story_optimizer = (
            story_optimizer
            or StoryOptimizer()
        )

    def generate(
        self,
        *,
        episode_id: str,
        topic: str,
        evidence_path: str | Path,
    ) -> Story:
        evidence_data = self._load_evidence(
            Path(evidence_path)
        )

        evidence_topic = str(
            evidence_data.get(
                "topic",
                "",
            )
        ).strip()

        resolved_topic = (
            topic.strip()
            or evidence_topic
        )

        if not resolved_topic:
            raise ValueError(
                "topic을 확인할 수 없습니다."
            )

        raw_items = evidence_data.get(
            "items",
            [],
        )

        if not isinstance(
            raw_items,
            list,
        ):
            raise ValueError(
                "Evidence items는 배열이어야 합니다."
            )

        story = self._story_planner.plan(
            MysteryStoryPlan(
                episode_id=episode_id,
                topic=resolved_topic,
                evidence_items=raw_items,
            )
        )

        return self._story_optimizer.optimize(
            story=story,
            topic=resolved_topic,
        ).story

    def build(
        self,
        *,
        episode_id: str,
        topic: str,
        evidence_path: str | Path,
        output_path: str | Path,
    ) -> Any:
        """
        Mystery Story를 생성하고 Factory Core를 통해
        Timeline을 만든 뒤 JSON으로 저장합니다.

        Factory Core와 Timeline Schema는 lazy import하여
        Plugin의 Story 생성 책임과 실행 환경을 분리합니다.
        """

        from factory_core import FactoryCore
        from timeline_schema import save_timeline

        story = self.generate(
            episode_id=episode_id,
            topic=topic,
            evidence_path=evidence_path,
        )

        result = (
            FactoryCore().build_with_result(
                story
            )
        )

        save_timeline(
            result.timeline,
            output_path,
        )

        return result

    def _load_evidence(
        self,
        path: Path,
    ) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(
                "Evidence 결과 파일이 없습니다: "
                f"{path}"
            )

        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        if not isinstance(
            data,
            dict,
        ):
            raise ValueError(
                "Evidence 결과의 최상위 값은 "
                "객체여야 합니다."
            )

        return data
