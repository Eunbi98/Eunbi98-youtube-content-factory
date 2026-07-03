from __future__ import annotations

import logging
import re

from app.story.script_qa import ScriptQAEngine
from app.story.text_normalizer import normalize_english_terms


logger = logging.getLogger(__name__)


class KoreanLanguageGuard:
    def __init__(
        self,
        min_korean_ratio: float = 0.45,
        max_english_ratio: float = 0.25,
    ) -> None:
        self.min_korean_ratio = min_korean_ratio
        self.max_english_ratio = max_english_ratio
        self.script_qa = ScriptQAEngine()

    def inspect(self, text: str) -> dict[str, float | int | bool]:
        normalized = normalize_english_terms(text)
        korean_count = len(re.findall(r"[가-힣]", normalized))
        english_count = len(re.findall(r"[A-Za-z]", normalized))
        total = korean_count + english_count

        korean_ratio = korean_count / total if total else 0.0
        english_ratio = english_count / total if total else 0.0
        has_english_sentence = bool(
            re.search(r"\b[A-Z][A-Za-z]+\s+[A-Za-z]{3,}\b", normalized)
        )

        return {
            "korean_count": korean_count,
            "english_count": english_count,
            "korean_ratio": korean_ratio,
            "english_ratio": english_ratio,
            "has_english_sentence": has_english_sentence,
            "is_korean_safe": (
                korean_ratio >= self.min_korean_ratio
                and english_ratio <= self.max_english_ratio
                and not has_english_sentence
            ),
        }

    def ensure_korean_script(
        self,
        script: str,
        story_plan: dict,
    ) -> str:
        normalized = normalize_english_terms(script)
        metrics = self.inspect(normalized)

        if metrics["is_korean_safe"]:
            return normalized

        logger.warning(
            "Korean guard fallback: korean_ratio=%.2f english_ratio=%.2f",
            metrics["korean_ratio"],
            metrics["english_ratio"],
        )

        return self.build_rule_based_fallback(story_plan)

    def build_rule_based_fallback(self, story_plan: dict) -> str:
        category = str(story_plan.get("category", "세계뉴스"))
        emotion = str(story_plan.get("emotion", "호기심"))
        hook = str(story_plan.get("hook", "")).strip()
        ending = str(story_plan.get("ending", "")).strip()

        middle_lines = self._middle_lines_for(category, emotion)
        raw_script = "\n".join(
            line
            for line in [hook, *middle_lines, ending]
            if line
        )

        return self.script_qa.polish_script(
            raw_script,
            protected_first=hook,
            protected_last=ending,
        )

    def _middle_lines_for(self, category: str, emotion: str) -> list[str]:
        category_lines = {
            "우주": [
                "먼 우주에서 뜻밖의 단서가 포착됐습니다.",
                "과학자들은 이 신호의 의미를 추적하고 있습니다.",
                "다음 관측이 해석을 바꿀 수 있습니다.",
            ],
            "과학": [
                "작은 발견이 큰 질문으로 이어졌습니다.",
                "연구진은 원인을 확인하기 위해 검증을 이어갑니다.",
                "결과에 따라 기존 설명이 달라질 수 있습니다.",
            ],
            "동물": [
                "현장에서는 예상 밖의 장면이 펼쳐졌습니다.",
                "사람들은 그 행동의 이유에 주목했습니다.",
                "이 이야기는 자연과 인간의 관계를 다시 보게 합니다.",
            ],
            "기술": [
                "새 기술은 일상 가까이 다가오고 있습니다.",
                "편리함만큼 안전성도 중요한 쟁점입니다.",
                "앞으로의 선택이 변화의 속도를 정할 것입니다.",
            ],
            "경제": [
                "시장에서는 작은 변화도 크게 번질 수 있습니다.",
                "전문가들은 다음 신호를 조심스럽게 보고 있습니다.",
                "이 흐름은 생활 가까이 영향을 줄 수 있습니다.",
            ],
        }

        if category in category_lines:
            return category_lines[category]

        if emotion == "긴장감":
            return [
                "상황은 빠르게 변하고 있습니다.",
                "핵심은 다음 대응에 달려 있습니다.",
                "사람들은 결과를 주의 깊게 지켜보고 있습니다.",
            ]

        return [
            "처음에는 작은 소식처럼 보였습니다.",
            "하지만 그 안에는 중요한 단서가 있었습니다.",
            "이제 사람들의 관심은 다음 장면으로 향합니다.",
        ]

    def sync_scenes_to_script(
        self,
        script: str,
        previous_scenes: list[dict] | None = None,
    ) -> list[dict]:
        previous_scenes = previous_scenes or []
        lines = [
            line.strip()
            for line in script.splitlines()
            if line.strip()
        ]
        synced = []

        for index, line in enumerate(lines, start=1):
            previous = (
                previous_scenes[index - 1]
                if index <= len(previous_scenes)
                and isinstance(previous_scenes[index - 1], dict)
                else {}
            )
            keyword = str(previous.get("image_keyword", "")).strip()

            try:
                duration = int(previous.get("duration", 4))
            except ValueError:
                duration = 4

            synced.append({
                "order": index,
                "text": line,
                "image_keyword": keyword,
                "duration": max(3, min(duration, 5)),
            })

        return synced
