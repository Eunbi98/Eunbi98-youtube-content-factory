from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Callable, Iterable

from .news_source import GoogleNewsTopicSource, TopicSource
from .topic_catalog import (
    ARCHIVE_TOPICS,
    BRAND_EXCLUDE_KEYWORDS,
    CATEGORY_KEYWORDS,
    CATEGORY_LABELS,
    CHANNEL_FIT_KEYWORDS,
    EXCLUDE_KEYWORDS,
    HOOK_KEYWORDS,
    LOW_QUALITY_SOURCE_KEYWORDS,
    SENSATIONAL_KEYWORDS,
    SOURCE_MODE_LABELS,
    TOPIC_MATCH_STOPWORDS,
    TRUSTED_SOURCE_KEYWORDS,
    VISUAL_KEYWORDS,
)
from .topic_models import TopicCandidate, TopicFinderResult, TopicSourceItem


class TopicFinderError(ValueError):
    """Auto Topic Finder 입력 또는 실행 오류."""


class AutoTopicFinder:
    def __init__(
        self,
        *,
        source: TopicSource | None = None,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._source = source or GoogleNewsTopicSource()
        self._now = now or (lambda: datetime.now(timezone.utc))

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(CATEGORY_LABELS)

    def find(
        self,
        *,
        category: str,
        limit: int = 10,
        excluded_topics: Iterable[str] = (),
        source_mode: str = "trend",
    ) -> TopicFinderResult:
        normalized_category = category.strip().lower()
        normalized_mode = source_mode.strip().lower()
        if normalized_category != "all" and normalized_category not in CATEGORY_LABELS:
            supported = ", ".join(("all", *CATEGORY_LABELS))
            raise TopicFinderError(
                "지원하지 않는 카테고리입니다. "
                f"요청: {category}, 지원: {supported}"
            )
        if limit < 1 or limit > 20:
            raise TopicFinderError("후보 개수는 1개 이상 20개 이하여야 합니다.")
        if normalized_mode not in SOURCE_MODE_LABELS:
            supported = ", ".join(SOURCE_MODE_LABELS)
            raise TopicFinderError(
                "지원하지 않는 수집 모드입니다. "
                f"요청: {source_mode}, 지원: {supported}"
            )

        excluded_topic_texts = tuple(excluded_topics)
        if normalized_category == "all":
            return self._find_all(
                limit=limit,
                excluded_topics=excluded_topic_texts,
                source_mode=normalized_mode,
            )

        warnings: list[str] = []
        source_items: list[TopicSourceItem] = []
        if normalized_mode != "archive":
            try:
                source_items = self._source.fetch(
                    category=normalized_category,
                    limit=max(limit * 6, 30),
                )
            except Exception as exc:  # 외부 뉴스 장애는 아카이브로 복구합니다.
                warnings.append(f"실시간 뉴스 수집 실패: {exc}")

        live_candidates = self._build_live_candidates(
            category=normalized_category,
            items=source_items,
            excluded_topics=excluded_topic_texts,
        )
        if normalized_mode == "archive":
            selected = self._build_archive_candidates(
                category=normalized_category,
                existing_topics=set(),
                excluded_topics=excluded_topic_texts,
                limit=limit,
            )
            mode = "archive"
        elif normalized_mode == "mixed":
            archive_target = (limit * 3 + 4) // 5
            trend_target = limit - archive_target
            selected = live_candidates[:trend_target]
            selected.extend(
                self._build_archive_candidates(
                    category=normalized_category,
                    existing_topics={item.topic for item in selected},
                    excluded_topics=excluded_topic_texts,
                    limit=archive_target,
                )
            )
            if len(selected) < limit:
                missing = limit - len(selected)
                selected.extend(
                    live_candidates[trend_target : trend_target + missing]
                )
            mode = "mixed" if live_candidates and any(
                item.source_count == 0 for item in selected
            ) else ("live" if live_candidates else "archive")
        else:
            selected = live_candidates[:limit]
            used_fallback = len(selected) < limit
            if used_fallback:
                selected.extend(
                    self._build_archive_candidates(
                        category=normalized_category,
                        existing_topics={item.topic for item in selected},
                        excluded_topics=excluded_topic_texts,
                        limit=limit - len(selected),
                    )
                )
            if live_candidates and used_fallback:
                mode = "hybrid"
            elif live_candidates:
                mode = "live"
            else:
                mode = "fallback"

        selected.sort(
            key=lambda item: (item.score, item.source_count, item.topic),
            reverse=True,
        )
        selected = selected[:limit]

        ranked = self._rank(selected)

        generated_at = self._as_utc(self._now()).isoformat()
        return TopicFinderResult(
            category=normalized_category,
            generated_at=generated_at,
            mode=mode,
            candidate_count=len(ranked),
            candidates=ranked,
            warnings=warnings,
        )

    def _find_all(
        self,
        *,
        limit: int,
        excluded_topics: tuple[str, ...],
        source_mode: str,
    ) -> TopicFinderResult:
        candidates: list[TopicCandidate] = []
        warnings: list[str] = []
        per_category_limit = max(5, limit)
        for category in CATEGORY_LABELS:
            result = self.find(
                category=category,
                limit=per_category_limit,
                excluded_topics=excluded_topics,
                source_mode=source_mode,
            )
            warnings.extend(result.warnings)
            for candidate in result.candidates:
                if any(
                    self._is_similar(candidate.topic, item.topic)
                    for item in candidates
                ):
                    continue
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: (item.score, item.source_count, item.topic),
            reverse=True,
        )
        ranked = self._rank(candidates[:limit])
        has_live = any(item.source_count > 0 for item in ranked)
        has_archive = any(item.source_count == 0 for item in ranked)
        if source_mode == "mixed":
            result_mode = (
                "mixed"
                if has_live and has_archive
                else ("live" if has_live else "archive")
            )
        elif source_mode == "trend" and has_archive:
            result_mode = "hybrid" if has_live else "fallback"
        else:
            result_mode = source_mode
        return TopicFinderResult(
            category="all",
            generated_at=self._as_utc(self._now()).isoformat(),
            mode=result_mode,
            candidate_count=len(ranked),
            candidates=ranked,
            warnings=list(dict.fromkeys(warnings)),
        )

    @staticmethod
    def _rank(items: list[TopicCandidate]) -> list[TopicCandidate]:
        return [
            TopicCandidate(
                rank=index,
                category=item.category,
                topic=item.topic,
                angle=item.angle,
                score=item.score,
                reasons=item.reasons,
                search_queries=item.search_queries,
                source_count=item.source_count,
                sources=item.sources,
            )
            for index, item in enumerate(items, start=1)
        ]

    def _build_live_candidates(
        self,
        *,
        category: str,
        items: list[TopicSourceItem],
        excluded_topics: tuple[str, ...],
    ) -> list[TopicCandidate]:
        groups: list[list[TopicSourceItem]] = []
        for item in items:
            topic = self._clean_title(item.title)
            if (
                not topic
                or self._is_low_quality_source(item.source)
                or self._is_excluded(topic)
                or self._is_brand_excluded(topic)
                or not self._is_channel_fit(category, topic)
                or self._is_already_covered(topic, excluded_topics)
            ):
                continue

            target_group = next(
                (
                    group
                    for group in groups
                    if self._is_similar(
                        topic,
                        self._clean_title(group[0].title),
                    )
                ),
                None,
            )
            if target_group is None:
                groups.append([item])
            else:
                target_group.append(item)

        candidates: list[TopicCandidate] = []
        for group in groups:
            representative = max(
                group,
                key=lambda item: self._base_score(
                    category=category,
                    topic=self._clean_title(item.title),
                    published_at=item.published_at,
                )[0],
            )
            topic = self._clean_title(representative.title)
            base_score, reasons = self._base_score(
                category=category,
                topic=topic,
                published_at=representative.published_at,
            )
            source_count = len({item.source for item in group})
            if source_count > 1:
                base_score += min(12, (source_count - 1) * 4)
                reasons.append(f"서로 다른 출처 {source_count}곳에서 다룸")

            trusted_source_count = sum(
                1 for item in group if self._is_trusted_source(item.source)
            )
            if trusted_source_count:
                base_score += min(10, trusted_source_count * 5)
                reasons.append("신뢰도 높은 언론·과학 출처에서 다룸")

            if self._keyword_hits(topic, SENSATIONAL_KEYWORDS):
                base_score -= 8
                reasons.append("과장형 제목 표현 감점")

            reasons.append("채널 브랜드 적합도 통과")

            candidates.append(
                TopicCandidate(
                    rank=0,
                    category=category,
                    topic=topic,
                    angle=self._build_angle(category, topic),
                    score=round(min(100.0, base_score), 1),
                    reasons=reasons,
                    search_queries=self._search_queries(category, topic),
                    source_count=source_count,
                    sources=group[:5],
                )
            )

        candidates.sort(
            key=lambda item: (item.score, item.source_count, item.topic),
            reverse=True,
        )
        return candidates

    def _build_archive_candidates(
        self,
        *,
        category: str,
        existing_topics: set[str],
        excluded_topics: tuple[str, ...],
        limit: int,
    ) -> list[TopicCandidate]:
        results: list[TopicCandidate] = []
        for index, topic in enumerate(ARCHIVE_TOPICS[category]):
            if (
                topic in existing_topics
                or self._is_already_covered(topic, excluded_topics)
            ):
                continue
            results.append(
                TopicCandidate(
                    rank=0,
                    category=category,
                    topic=topic,
                    angle=self._build_angle(category, topic),
                    score=round(74.0 - index * 0.8, 1),
                    reasons=[
                        "채널 성격과 맞는 미스터리 아카이브 주제",
                        "공식·학술 자료로 재검증할 상시 관심 후보",
                        "채널 브랜드 적합도 통과",
                    ],
                    search_queries=self._search_queries(category, topic),
                )
            )
            if len(results) >= limit:
                break
        return results

    def _base_score(
        self,
        *,
        category: str,
        topic: str,
        published_at: str | None,
    ) -> tuple[float, list[str]]:
        score = 42.0
        reasons: list[str] = []

        recency_score = self._recency_score(published_at)
        score += recency_score
        if recency_score >= 15:
            reasons.append("최근 7일 이내 보도")

        category_hits = self._keyword_hits(topic, CATEGORY_KEYWORDS[category])
        if category_hits:
            score += min(20, category_hits * 5)
            reasons.append(
                f"{CATEGORY_LABELS[category]} 핵심 키워드 {category_hits}개 포함"
            )

        hook_hits = self._keyword_hits(topic, HOOK_KEYWORDS)
        if hook_hits:
            score += min(12, hook_hits * 4)
            reasons.append("제목 훅으로 만들기 좋은 발견·의문 요소")

        visual_hits = self._keyword_hits(topic, VISUAL_KEYWORDS)
        if visual_hits:
            score += min(8, visual_hits * 2)
            reasons.append("영상 자료로 표현하기 쉬운 주제")

        if not reasons:
            reasons.append("최근 뉴스에서 수집된 카테고리 관련 주제")
        return score, reasons

    def _recency_score(self, published_at: str | None) -> float:
        if not published_at:
            return 4.0
        try:
            published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except ValueError:
            return 4.0

        age = self._as_utc(self._now()) - self._as_utc(published)
        hours = max(0.0, age.total_seconds() / 3600)
        if hours <= 24:
            return 25.0
        if hours <= 72:
            return 21.0
        if hours <= 168:
            return 16.0
        if hours <= 336:
            return 9.0
        return 3.0

    @staticmethod
    def _clean_title(raw_title: str) -> str:
        title = " ".join(raw_title.strip().split())
        parts = title.rsplit(" - ", 1)
        if len(parts) == 2 and len(parts[0]) >= 8:
            title = parts[0]
        return title.strip(" '\"“”‘’")[:120]

    @staticmethod
    def _keyword_hits(text: str, keywords: set[str]) -> int:
        lowered = text.casefold()
        return sum(1 for keyword in keywords if keyword.casefold() in lowered)

    @staticmethod
    def _is_excluded(topic: str) -> bool:
        lowered = topic.casefold()
        return any(keyword.casefold() in lowered for keyword in EXCLUDE_KEYWORDS)

    @staticmethod
    def _is_brand_excluded(topic: str) -> bool:
        lowered = topic.casefold()
        return any(
            keyword.casefold() in lowered for keyword in BRAND_EXCLUDE_KEYWORDS
        )

    @staticmethod
    def _is_channel_fit(category: str, topic: str) -> bool:
        lowered = topic.casefold()
        return any(
            keyword.casefold() in lowered
            for keyword in CHANNEL_FIT_KEYWORDS[category]
        )

    @staticmethod
    def _is_low_quality_source(source: str) -> bool:
        lowered = source.casefold()
        return any(
            keyword.casefold() in lowered
            for keyword in LOW_QUALITY_SOURCE_KEYWORDS
        )

    @staticmethod
    def _is_trusted_source(source: str) -> bool:
        lowered = source.casefold()
        return any(
            keyword.casefold() in lowered
            for keyword in TRUSTED_SOURCE_KEYWORDS
        )

    @classmethod
    def _is_already_covered(
        cls,
        topic: str,
        excluded_topics: tuple[str, ...],
    ) -> bool:
        topic_tokens = cls._match_tokens(topic)
        if not topic_tokens:
            return False
        for existing in excluded_topics:
            existing_tokens = cls._match_tokens(existing)
            if len(topic_tokens & existing_tokens) >= 3:
                return True
        return False

    @classmethod
    def _is_similar(cls, left: str, right: str) -> bool:
        left_tokens = cls._tokens(left)
        right_tokens = cls._tokens(right)
        if not left_tokens or not right_tokens:
            return left == right
        overlap = len(left_tokens & right_tokens)
        return overlap / min(len(left_tokens), len(right_tokens)) >= 0.55

    @staticmethod
    def _tokens(text: str) -> set[str]:
        stopwords = {
            "관련",
            "대한",
            "통해",
            "에서",
            "으로",
            "한다",
            "했다",
            "밝혀",
            "뉴스",
        }
        return {
            AutoTopicFinder._strip_korean_suffix(token.casefold())
            for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", text)
            if token.casefold() not in stopwords
        }

    @classmethod
    def _match_tokens(cls, text: str) -> set[str]:
        return {
            token
            for token in cls._tokens(text)
            if token not in TOPIC_MATCH_STOPWORDS and len(token) >= 2
        }

    @staticmethod
    def _strip_korean_suffix(token: str) -> str:
        suffixes = (
            "에서는",
            "에게서",
            "으로는",
            "이라는",
            "에서",
            "에게",
            "으로",
            "에는",
            "까지",
            "부터",
            "처럼",
            "보다",
            "의",
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "에",
            "도",
            "와",
            "과",
        )
        for suffix in suffixes:
            if token.endswith(suffix) and len(token) >= len(suffix) + 2:
                return token[: -len(suffix)]
        return token

    @staticmethod
    def _build_angle(category: str, topic: str) -> str:
        templates = {
            "mystery": f"{topic}에서 아직 풀리지 않은 핵심은 무엇일까?",
            "science": f"{topic}이 우리의 상식을 어떻게 바꿀까?",
            "history": f"{topic}이 기존 역사 해석을 어떻게 바꿀까?",
            "space": f"{topic}이 우주에 대해 무엇을 새로 알려줄까?",
        }
        return templates[category]

    @staticmethod
    def _search_queries(category: str, topic: str) -> list[str]:
        label = CATEGORY_LABELS[category]
        return [
            topic,
            f"{topic} 최신 연구 공식 발표",
            f"{topic} 사실 확인 반박",
            f"{topic} {label} 사진 영상 자료",
        ]

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    SOURCE_MODE_LABELS,
