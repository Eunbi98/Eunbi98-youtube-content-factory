from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from story_graph import (
    Answer,
    Ending,
    Fact,
    Hook,
    Narrative,
    Story,
    StoryMedia,
)


@dataclass(frozen=True)
class MysteryStoryPlan:
    """
    Mystery Story Planner의 입력 데이터입니다.
    """

    episode_id: str
    topic: str
    evidence_items: list[dict[str, Any]]


class MysteryStoryPlanner:
    """
    EvidenceResult를 Story Graph로 변환합니다.

    기본 구조:

    Hook
    -> Answer
    -> Story
    -> Fact
    -> Ending

    Story Planner는 Timeline 시간이나 연출을 결정하지 않습니다.
    해당 책임은 Factory Core와 Director에 있습니다.
    """

    def plan(
        self,
        plan: MysteryStoryPlan,
    ) -> Story:
        topic = self._normalize_text(
            plan.topic
        )

        if not topic:
            raise ValueError(
                "topic은 비어 있을 수 없습니다."
            )

        if not plan.episode_id.strip():
            raise ValueError(
                "episode_id는 비어 있을 수 없습니다."
            )

        evidence_items = self._select_evidence(
            plan.evidence_items
        )

        primary = evidence_items[0]
        secondary = evidence_items[1]
        counterpoint = self._find_counterpoint(
            evidence_items
        )

        return Story(
            episode_id=plan.episode_id.strip(),
            title=f"{topic}, 정말 사실일까?",
            beats=[
                Hook(
                    title=f"{topic}, 정말 사실일까?",
                    narration=(
                        f"{topic}에 관한 이야기는 "
                        "오랫동안 사실처럼 전해졌습니다. "
                        "그런데 실제 기록도 같은 이야기를 하고 있을까요?"
                    ),
                    subtitle=(
                        f"{topic},\n정말 사실일까?"
                    ),
                    media=self._color_media(),
                    keywords=[
                        topic,
                        "미스터리",
                        "실제 기록",
                    ],
                ),
                Answer(
                    title="기록부터 확인해 보면",
                    narration=(
                        f"확인 가능한 자료에서 가장 먼저 보이는 내용은 "
                        f"{primary['claim']}"
                    ),
                    subtitle=(
                        "먼저 실제 기록부터\n확인해 봤습니다"
                    ),
                    media=self._color_media(),
                    keywords=self._build_keywords(
                        topic,
                        primary,
                    ),
                ),
                Narrative(
                    title="가장 흥미로운 실제 사례",
                    narration=(
                        f"그중 특히 눈에 띄는 사례는 "
                        f"{secondary['claim']}"
                    ),
                    subtitle=(
                        "가장 눈에 띄는\n실제 사례"
                    ),
                    media=self._color_media(),
                    keywords=self._build_keywords(
                        topic,
                        secondary,
                    ),
                ),
                Fact(
                    title="하지만 다른 설명도 있습니다",
                    narration=(
                        f"하지만 모든 기록이 미스터리를 지지하는 것은 아닙니다. "
                        f"{counterpoint['claim']}"
                    ),
                    subtitle=(
                        "하지만 반대되는\n설명도 있습니다"
                    ),
                    media=self._color_media(),
                    keywords=self._build_keywords(
                        topic,
                        counterpoint,
                    ),
                ),
                Ending(
                    title="당신은 어떻게 생각하나요?",
                    narration=(
                        f"결국 {topic}은 완전히 해결된 이야기도, "
                        "모든 것이 미스터리인 이야기도 아닙니다. "
                        "당신은 어떤 설명이 더 설득력 있다고 생각하나요?"
                    ),
                    subtitle=(
                        "당신은 어떤 설명이\n더 설득력 있나요?"
                    ),
                    media=self._color_media(),
                    keywords=[
                        topic,
                        "미해결",
                        "의견",
                    ],
                ),
            ],
        )

    def _select_evidence(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        valid_items = [
            item
            for item in items
            if self._is_valid_item(item)
        ]

        if len(valid_items) < 2:
            raise ValueError(
                "Story 생성에는 최소 2개의 "
                "유효한 Evidence가 필요합니다."
            )

        return sorted(
            valid_items,
            key=lambda item: float(
                item.get(
                    "total_score",
                    0.0,
                )
            ),
            reverse=True,
        )

    def _find_counterpoint(
        self,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        for item in items:
            if (
                item.get("evidence_type")
                == "counterpoint"
            ):
                return item

        return items[-1]

    def _is_valid_item(
        self,
        item: dict[str, Any],
    ) -> bool:
        return bool(
            self._normalize_text(
                str(item.get("claim", ""))
            )
            and self._normalize_text(
                str(item.get("title", ""))
            )
        )

    def _build_keywords(
        self,
        topic: str,
        item: dict[str, Any],
    ) -> list[str]:
        values = [
            topic,
            *[
                str(keyword)
                for keyword in item.get(
                    "keywords",
                    [],
                )
            ],
        ]

        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            normalized = self._normalize_text(
                value
            )

            if (
                normalized
                and normalized not in seen
            ):
                seen.add(normalized)
                result.append(normalized)

        return result

    @staticmethod
    def _color_media() -> StoryMedia:
        """
        실제 Media Selector 연결 전까지
        안전한 color media를 사용합니다.
        """

        return StoryMedia(
            type="color",
        )

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        return " ".join(
            value.strip().split()
        )
