from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from story_graph import Story
from story_planner import (
    MysteryStoryPlan,
    MysteryStoryPlanner,
)


class MysteryPlugin:
    """
    Mystery 장르의 Story 생성 진입점입니다.

    Core는 장르를 모르며,
    Mystery Plugin만 Mystery Story 구조를 알고 있습니다.
    """

    def __init__(
        self,
        *,
        story_planner: (
            MysteryStoryPlanner | None
        ) = None,
    ) -> None:
        self._story_planner = (
            story_planner
            or MysteryStoryPlanner()
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

        return self._story_planner.plan(
            MysteryStoryPlan(
                episode_id=episode_id,
                topic=resolved_topic,
                evidence_items=raw_items,
            )
        )

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

        if not isinstance(data, dict):
            raise ValueError(
                "Evidence 결과의 최상위 값은 "
                "객체여야 합니다."
            )

        return data
