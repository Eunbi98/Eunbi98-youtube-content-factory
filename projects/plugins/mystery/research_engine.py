from __future__ import annotations

import re

from research_schema import (
    ResearchQuestion,
    ResearchResult,
    SourceRecommendation,
)


class MysteryResearchEngine:
    """
    Mystery Plugin용 초기 Research Engine입니다.

    외부 웹 검색을 직접 수행하지 않고,
    주제를 분석해 조사 계획과 검색 키워드를 생성합니다.

    다음 Feature에서 Evidence Collector가 이 결과를 받아
    실제 자료 수집과 검증을 수행합니다.
    """

    def build(
        self,
        topic: str,
    ) -> ResearchResult:
        normalized_topic = self._normalize_topic(
            topic
        )

        self._validate_topic(
            normalized_topic
        )

        search_keywords = (
            self._build_search_keywords(
                normalized_topic
            )
        )

        research_questions = (
            self._build_research_questions(
                normalized_topic
            )
        )

        recommended_sources = (
            self._build_source_recommendations(
                normalized_topic
            )
        )

        story_angles = (
            self._build_story_angles(
                normalized_topic
            )
        )

        return ResearchResult(
            topic=topic.strip(),
            normalized_topic=normalized_topic,
            search_keywords=search_keywords,
            research_questions=research_questions,
            recommended_sources=(
                recommended_sources
            ),
            story_angles=story_angles,
            notes=[
                (
                    "이 결과는 조사 계획입니다. "
                    "사실 데이터는 Evidence Collector에서 채웁니다."
                )
            ],
        )

    def _normalize_topic(
        self,
        topic: str,
    ) -> str:
        normalized = re.sub(
            r"\s+",
            " ",
            topic.strip(),
        )

        return normalized

    def _validate_topic(
        self,
        topic: str,
    ) -> None:
        if not topic:
            raise ValueError(
                "topic은 비어 있을 수 없습니다."
            )

        if len(topic) < 2:
            raise ValueError(
                "topic은 2글자 이상이어야 합니다."
            )

        if len(topic) > 100:
            raise ValueError(
                "topic은 100글자를 초과할 수 없습니다."
            )

    def _build_search_keywords(
        self,
        topic: str,
    ) -> list[str]:
        candidates = [
            topic,
            f"{topic} 역사",
            f"{topic} 실제 사건",
            f"{topic} 공식 기록",
            f"{topic} 연구",
            f"{topic} 미스터리",
            f"{topic} 반박",
            f"{topic} 최근 발견",
            f"{topic} 전문가 분석",
            f"{topic} 사진 자료",
        ]

        return self._deduplicate(
            candidates
        )

    def _build_research_questions(
        self,
        topic: str,
    ) -> list[ResearchQuestion]:
        questions = [
            ResearchQuestion(
                id="origin",
                category="background",
                question=(
                    f"{topic}은 무엇이며 "
                    "언제부터 알려졌는가?"
                ),
                priority=1,
            ),
            ResearchQuestion(
                id="core_claim",
                category="claim",
                question=(
                    f"{topic}과 관련해 가장 널리 알려진 "
                    "주장은 무엇인가?"
                ),
                priority=1,
            ),
            ResearchQuestion(
                id="evidence",
                category="evidence",
                question=(
                    f"{topic}의 주장을 뒷받침하는 "
                    "확인 가능한 근거는 무엇인가?"
                ),
                priority=1,
            ),
            ResearchQuestion(
                id="counter_evidence",
                category="verification",
                question=(
                    f"{topic}에 대한 반박이나 "
                    "대안 설명은 무엇인가?"
                ),
                priority=2,
            ),
            ResearchQuestion(
                id="case",
                category="case",
                question=(
                    f"{topic}과 관련된 가장 흥미로운 "
                    "실제 사례는 무엇인가?"
                ),
                priority=2,
            ),
            ResearchQuestion(
                id="visual",
                category="visual",
                question=(
                    f"{topic}을 영상으로 보여줄 수 있는 "
                    "장소, 인물, 유물, 기록은 무엇인가?"
                ),
                priority=3,
            ),
            ResearchQuestion(
                id="ending",
                category="ending",
                question=(
                    f"{topic}에 대해 현재도 "
                    "해결되지 않은 질문은 무엇인가?"
                ),
                priority=3,
            ),
        ]

        return questions

    def _build_source_recommendations(
        self,
        topic: str,
    ) -> list[SourceRecommendation]:
        return [
            SourceRecommendation(
                tier="official",
                purpose=(
                    "사건, 장소, 기록의 기본 사실 확인"
                ),
                query_hint=(
                    f"{topic} site:gov OR site:go.kr "
                    "official archive"
                ),
            ),
            SourceRecommendation(
                tier="academic",
                purpose=(
                    "연구 결과와 전문적 해석 확인"
                ),
                query_hint=(
                    f"{topic} research paper study"
                ),
            ),
            SourceRecommendation(
                tier="reference",
                purpose=(
                    "연대표와 배경 맥락 정리"
                ),
                query_hint=(
                    f"{topic} encyclopedia history"
                ),
            ),
            SourceRecommendation(
                tier="news",
                purpose=(
                    "최근 발견과 후속 보도 확인"
                ),
                query_hint=(
                    f"{topic} latest discovery news"
                ),
            ),
        ]

    def _build_story_angles(
        self,
        topic: str,
    ) -> list[str]:
        return [
            (
                f"{topic}은 정말 사실일까?"
            ),
            (
                f"{topic}에서 사람들이 가장 많이 "
                "오해하는 것은 무엇일까?"
            ),
            (
                f"{topic}을 설명하는 가장 현실적인 "
                "가설은 무엇일까?"
            ),
            (
                f"{topic}의 실제 기록 중 가장 "
                "놀라운 사례는 무엇일까?"
            ),
            (
                f"{topic}에는 아직도 풀리지 않은 "
                "부분이 남아 있을까?"
            ),
        ]

    @staticmethod
    def _deduplicate(
        values: list[str],
    ) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []

        for value in values:
            normalized = value.strip()

            if (
                normalized
                and normalized not in seen
            ):
                seen.add(normalized)
                result.append(normalized)

        return result
