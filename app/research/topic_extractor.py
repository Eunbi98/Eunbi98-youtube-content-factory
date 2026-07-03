from __future__ import annotations

import re

from app.research.research_types import ResearchInput
from app.story.text_normalizer import normalize_english_terms


class TopicExtractor:
    def extract(self, item: ResearchInput) -> str:
        text = normalize_english_terms(item.combined_text())
        lowered = text.lower()

        if self._contains_any(lowered, ["webb", "james webb", "제임스 웹"]):
            if self._contains_any(lowered, ["signal", "신호", "mystery", "unknown", "미스터리"]):
                return "제임스 웹 우주망원경이 포착한 미스터리 신호"
            return "제임스 웹 우주망원경이 보여준 새로운 우주 단서"

        if self._contains_any(lowered, ["nasa", "나사", "telescope", "우주망원경"]):
            return "나사 관측 자료가 던진 새로운 우주 질문"

        if self._contains_any(lowered, ["ai", "robot", "로봇", "인공지능"]):
            return "사람의 행동을 따라 배우는 인공지능 로봇"

        if self._contains_any(lowered, ["whale", "고래", "rescue", "구조"]):
            return "해안에서 구조된 고래가 남긴 메시지"

        if self._contains_any(lowered, ["climate", "기후", "earthquake", "지진", "volcano", "화산"]):
            return "자연이 보내는 이상 신호"

        cleaned_title = self._clean_title(text.splitlines()[0] if text else "")

        if cleaned_title:
            return f"{cleaned_title}에 숨은 이야기"

        return "오늘 뉴스가 던진 핵심 질문"

    def _contains_any(self, text: str, keywords: list[str]) -> bool:
        return any(keyword.lower() in text for keyword in keywords)

    def _clean_title(self, title: str) -> str:
        title = normalize_english_terms(title)
        title = re.sub(r"[^가-힣A-Za-z0-9\s]", " ", title)
        title = re.sub(r"\s+", " ", title).strip()

        if len(title) > 24:
            title = title[:24].rstrip()

        return title
