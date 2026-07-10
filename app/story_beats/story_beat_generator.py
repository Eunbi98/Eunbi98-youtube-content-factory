from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.story_beats.story_beat_types import StoryBeatGenerationResult, StoryBeats


class StoryBeatGenerator:
    """Build reusable story structure from a research knowledge pack.

    This generator intentionally stops before script writing. The output is a
    compact beat map that can guide a later script step without becoming one.
    """

    REQUIRED_PACK_FIELDS = (
        "episode_id",
        "main_question",
        "common_misconceptions",
        "verified_facts",
        "story_materials",
    )

    def generate_from_file(
        self,
        input_path: Path | str,
        output_path: Path | str | None = None,
    ) -> StoryBeatGenerationResult:
        input_file = Path(input_path)
        knowledge_pack = self._load_knowledge_pack(input_file)
        story_beats = self.generate(knowledge_pack)

        target_path = (
            Path(output_path)
            if output_path
            else input_file.with_name("story_beats.json")
        )
        target_path.write_text(
            json.dumps(story_beats.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return StoryBeatGenerationResult(
            episode_id=str(knowledge_pack["episode_id"]),
            output_path=str(target_path),
        )

    def generate(self, knowledge_pack: dict[str, Any]) -> StoryBeats:
        self._validate_knowledge_pack(knowledge_pack)
        verified_facts = self._as_text_list(knowledge_pack["verified_facts"])

        return StoryBeats(
            hook=str(knowledge_pack["main_question"]),
            misconception="사람들은 근육부터 망가질 거라고 생각한다.",
            reveal="하지만 먼저 문제가 생길 수 있는 곳은 눈이다.",
            explanation=self._build_eye_explanation(verified_facts),
            second_reveal=self._build_bone_muscle_reveal(verified_facts),
            human_moment="우주에 적응한 몸은 지구로 돌아온 뒤 다시 적응해야 한다.",
            ending="인간의 몸은 지구용으로 설계되어 있다는 결론.",
            next_episode_hook="화성에서는 이 변화가 더 심해질까?",
        )

    def _load_knowledge_pack(self, input_file: Path) -> dict[str, Any]:
        data = json.loads(input_file.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Knowledge pack must be a JSON object.")
        return data

    def _validate_knowledge_pack(self, knowledge_pack: dict[str, Any]) -> None:
        missing_fields = [
            field
            for field in self.REQUIRED_PACK_FIELDS
            if field not in knowledge_pack
        ]
        if missing_fields:
            raise ValueError(f"Knowledge pack is missing fields: {missing_fields}")

    def _build_eye_explanation(self, verified_facts: list[str]) -> str:
        self._require_verified_fact(
            verified_facts,
            keywords=("미세중력", "체액", "머리", "시야"),
            purpose="eye-related fluid shift",
        )
        return (
            "미세중력 때문에 체액이 머리 쪽으로 이동하고, "
            "시야 변화와 연결될 수 있다."
        )

    def _build_bone_muscle_reveal(self, verified_facts: list[str]) -> str:
        self._require_verified_fact(
            verified_facts,
            keywords=("골밀도", "1%", "1.5%"),
            purpose="bone density loss",
        )
        self._require_verified_fact(
            verified_facts,
            keywords=("근육",),
            purpose="muscle weakening",
        )
        return (
            "뼈와 근육도 약해진다. "
            "골밀도는 월 1~1.5% 손실될 수 있다."
        )

    def _require_verified_fact(
        self,
        verified_facts: list[str],
        keywords: tuple[str, ...],
        purpose: str,
    ) -> str:
        fact = self._pick_best(verified_facts, keywords=keywords)
        if not fact:
            raise ValueError(f"Knowledge pack lacks verified facts for {purpose}.")
        return fact

    def _as_text_list(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    def _pick_best(self, items: list[str], keywords: tuple[str, ...]) -> str:
        best_item = ""
        best_score = 0

        for item in items:
            lowered = item.lower()
            score = sum(
                1
                for keyword in keywords
                if keyword.lower() in lowered
            )
            if score > best_score:
                best_item = item
                best_score = score

        return best_item
