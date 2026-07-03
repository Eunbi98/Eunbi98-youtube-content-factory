from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import TypeVar

from app.story.ending_library import select_ending
from app.story.hook_library import select_hook
from app.story.story_types import Category, Emotion, NewsInput, StoryEngineResult, StorySection


logger = logging.getLogger(__name__)

LabelT = TypeVar("LabelT", Category, Emotion)


CATEGORY_KEYWORDS: dict[Category, tuple[str, ...]] = {
    "우주": (
        "우주",
        "행성",
        "은하",
        "별",
        "천문",
        "망원경",
        "nasa",
        "space",
        "planet",
        "galaxy",
        "webb",
        "tess",
    ),
    "과학": (
        "과학",
        "연구",
        "실험",
        "발견",
        "논문",
        "세포",
        "유전자",
        "science",
        "research",
        "study",
    ),
    "동물": (
        "동물",
        "고래",
        "상어",
        "새",
        "강아지",
        "고양이",
        "멸종",
        "animal",
        "whale",
        "shark",
    ),
    "기술": (
        "기술",
        "ai",
        "인공지능",
        "로봇",
        "반도체",
        "스마트폰",
        "앱",
        "데이터",
        "technology",
        "robot",
    ),
    "역사": (
        "역사",
        "고대",
        "유적",
        "왕",
        "전쟁",
        "문명",
        "발굴",
        "history",
        "ancient",
    ),
    "미스터리": (
        "미스터리",
        "실종",
        "정체불명",
        "수수께끼",
        "의문",
        "비밀",
        "mystery",
        "unknown",
    ),
    "세계뉴스": (
        "정부",
        "대통령",
        "전쟁",
        "외교",
        "국제",
        "국가",
        "시위",
        "선거",
        "world",
        "global",
    ),
    "자연": (
        "자연",
        "화산",
        "지진",
        "태풍",
        "기후",
        "바다",
        "숲",
        "빙하",
        "nature",
        "climate",
    ),
    "경제": (
        "경제",
        "시장",
        "주가",
        "금리",
        "물가",
        "투자",
        "기업",
        "매출",
        "economy",
        "market",
    ),
    "문화": (
        "문화",
        "영화",
        "음악",
        "드라마",
        "예술",
        "축제",
        "책",
        "공연",
        "culture",
        "film",
    ),
}

EMOTION_KEYWORDS: dict[Emotion, tuple[str, ...]] = {
    "호기심": (
        "왜",
        "어떻게",
        "가능성",
        "질문",
        "분석",
        "단서",
        "why",
        "how",
        "could",
    ),
    "충격": (
        "충격",
        "논란",
        "급락",
        "폭발",
        "사망",
        "위기",
        "shock",
        "stunning",
        "crisis",
    ),
    "미스터리": (
        "미스터리",
        "수수께끼",
        "정체불명",
        "알 수 없는",
        "비밀",
        "의문",
        "mystery",
        "unknown",
    ),
    "감동": (
        "감동",
        "구조",
        "기부",
        "회복",
        "희망",
        "가족",
        "rescue",
        "hope",
    ),
    "긴장감": (
        "긴장",
        "경고",
        "위험",
        "갈등",
        "추적",
        "대응",
        "warning",
        "risk",
    ),
    "경이로움": (
        "놀라운",
        "경이",
        "최초",
        "역대",
        "아름다운",
        "신비로운",
        "amazing",
        "first",
    ),
}


class StoryDirector:
    """Rule-based Story Engine v1 for immersive short-form news scripts."""

    def create_story(
        self,
        title: str,
        summary: str,
        source: str = "",
        url: str = "",
    ) -> dict[str, object]:
        news = NewsInput(title=title, summary=summary, source=source, url=url)
        logger.info("Creating story plan for title=%s", title)
        return self.create_story_from_news(news)

    def create_story_from_mapping(
        self,
        news: Mapping[str, str],
    ) -> dict[str, object]:
        return self.create_story(
            title=news.get("title", ""),
            summary=news.get("summary", ""),
            source=news.get("source", ""),
            url=news.get("url", ""),
        )

    def create_story_from_news(self, news: NewsInput) -> dict[str, object]:
        result = self._build_story_rule_based(news)
        return result.to_dict()

    def _build_story_rule_based(self, news: NewsInput) -> StoryEngineResult:
        category = self.estimate_category(news)
        emotion = self.estimate_emotion(news, category)
        hook = select_hook(category, emotion)
        ending = select_ending(category, emotion)

        return StoryEngineResult(
            category=category,
            emotion=emotion,
            hook=hook,
            story_structure=self._build_story_structure(),
            ending=ending,
            source=news.source,
            url=news.url,
        )

    def estimate_category(self, news: NewsInput) -> Category:
        text = self._normalize(news.combined_text())
        scores = self._score_keywords(text, CATEGORY_KEYWORDS)
        category = self._select_best(scores, default="세계뉴스")
        logger.info("Estimated category=%s", category)
        return category

    def estimate_emotion(self, news: NewsInput, category: Category) -> Emotion:
        text = self._normalize(news.combined_text())
        scores = self._score_keywords(text, EMOTION_KEYWORDS)

        default_by_category: dict[Category, Emotion] = {
            "우주": "경이로움",
            "과학": "호기심",
            "동물": "감동",
            "기술": "호기심",
            "역사": "미스터리",
            "미스터리": "미스터리",
            "세계뉴스": "긴장감",
            "자연": "경이로움",
            "경제": "긴장감",
            "문화": "감동",
        }
        emotion = self._select_best(scores, default=default_by_category[category])
        logger.info("Estimated emotion=%s", emotion)
        return emotion

    def _build_story_structure(self) -> list[StorySection]:
        return [
            StorySection(
                section="hook",
                purpose="시청자 관심 유도",
                target_seconds=5,
            ),
            StorySection(
                section="setup",
                purpose="상황 설명",
                target_seconds=10,
            ),
            StorySection(
                section="tension",
                purpose="궁금증 강화",
                target_seconds=12,
            ),
            StorySection(
                section="reveal",
                purpose="핵심 정보 공개",
                target_seconds=15,
            ),
            StorySection(
                section="ending",
                purpose="여운 있는 마무리",
                target_seconds=10,
            ),
        ]

    def _score_keywords(
        self,
        text: str,
        keyword_map: Mapping[LabelT, tuple[str, ...]],
    ) -> dict[LabelT, int]:
        return {
            label: sum(1 for keyword in keywords if keyword in text)
            for label, keywords in keyword_map.items()
        }

    def _select_best(self, scores: Mapping[LabelT, int], default: LabelT) -> LabelT:
        best_label = default
        best_score = 0

        for label, score in scores.items():
            if score > best_score:
                best_label = label
                best_score = score

        return best_label

    def _normalize(self, text: str) -> str:
        return text.lower()
