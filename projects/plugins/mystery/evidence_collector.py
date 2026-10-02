from __future__ import annotations

import hashlib
import re
from urllib.parse import urlparse

from evidence_schema import (
    EvidenceItem,
    EvidenceResult,
    RawEvidence,
)


SOURCE_RELIABILITY: dict[str, float] = {
    "official": 1.00,
    "academic": 0.95,
    "reference": 0.80,
    "news": 0.70,
    "unknown": 0.45,
}

TYPE_INTEREST: dict[str, float] = {
    "case": 0.95,
    "counterpoint": 0.90,
    "timeline": 0.80,
    "fact": 0.75,
    "quote": 0.65,
}

VISUAL_KEYWORDS = {
    "사진",
    "영상",
    "지도",
    "유적",
    "장소",
    "인물",
    "기록",
    "위성",
    "발견",
    "현장",
    "photo",
    "video",
    "map",
    "site",
    "ruins",
    "satellite",
    "discovery",
}


class EvidenceCollector:
    """
    외부 수집기가 전달한 RawEvidence를
    Mystery Plugin에서 사용할 EvidenceResult로 변환합니다.

    책임:

    - 필수값 검증
    - URL 및 텍스트 정규화
    - 중복 근거 제거
    - 신뢰도/흥미도/시각화 점수 계산
    - 전체 점수 기준 정렬

    실제 웹 요청은 수행하지 않습니다.
    웹 수집기는 이후 Adapter로 분리해 연결합니다.
    """

    def collect(
        self,
        *,
        topic: str,
        raw_items: list[RawEvidence],
    ) -> EvidenceResult:
        normalized_topic = self._normalize_text(
            topic
        )

        if not normalized_topic:
            raise ValueError(
                "topic은 비어 있을 수 없습니다."
            )

        accepted: list[EvidenceItem] = []
        seen_keys: set[str] = set()

        rejected_count = 0
        duplicate_count = 0

        for raw_item in raw_items:
            normalized = self._normalize_raw(
                raw_item
            )

            if normalized is None:
                rejected_count += 1
                continue

            duplicate_key = self._duplicate_key(
                normalized
            )

            if duplicate_key in seen_keys:
                duplicate_count += 1
                continue

            seen_keys.add(duplicate_key)

            accepted.append(
                self._build_item(
                    normalized
                )
            )

        accepted.sort(
            key=lambda item: (
                item.total_score,
                item.reliability_score,
                item.interest_score,
            ),
            reverse=True,
        )

        return EvidenceResult(
            topic=normalized_topic,
            items=accepted,
            rejected_count=rejected_count,
            duplicate_count=duplicate_count,
        )

    def _normalize_raw(
        self,
        item: RawEvidence,
    ) -> RawEvidence | None:
        title = self._normalize_text(
            item.title
        )

        claim = self._normalize_text(
            item.claim
        )

        source_name = self._normalize_text(
            item.source_name
        )

        source_url = item.source_url.strip()

        if (
            not title
            or not claim
            or not source_name
            or not self._is_valid_url(
                source_url
            )
        ):
            return None

        keywords = self._deduplicate(
            [
                self._normalize_text(
                    keyword
                )
                for keyword in item.keywords
            ]
        )

        return RawEvidence(
            title=title,
            claim=claim,
            source_name=source_name,
            source_url=source_url,
            source_tier=item.source_tier,
            evidence_type=item.evidence_type,
            published_at=item.published_at,
            keywords=keywords,
        )

    def _build_item(
        self,
        item: RawEvidence,
    ) -> EvidenceItem:
        reliability_score = (
            SOURCE_RELIABILITY[
                item.source_tier
            ]
        )

        interest_score = self._calculate_interest(
            item
        )

        visual_score = self._calculate_visual(
            item
        )

        total_score = round(
            reliability_score * 0.50
            + interest_score * 0.30
            + visual_score * 0.20,
            3,
        )

        return EvidenceItem(
            id=self._build_id(item),
            title=item.title,
            claim=item.claim,
            source_name=item.source_name,
            source_url=item.source_url,
            source_tier=item.source_tier,
            evidence_type=item.evidence_type,
            published_at=item.published_at,
            keywords=list(item.keywords),
            reliability_score=round(
                reliability_score,
                3,
            ),
            interest_score=round(
                interest_score,
                3,
            ),
            visual_score=round(
                visual_score,
                3,
            ),
            total_score=total_score,
        )

    def _calculate_interest(
        self,
        item: RawEvidence,
    ) -> float:
        base = TYPE_INTEREST[
            item.evidence_type
        ]

        claim_length = len(
            self._normalize_text(
                item.claim
            )
        )

        if 40 <= claim_length <= 180:
            base += 0.05

        if any(
            token in item.claim
            for token in (
                "하지만",
                "반면",
                "실제로",
                "처음",
                "유일",
                "가장",
                "however",
                "actually",
                "first",
                "only",
            )
        ):
            base += 0.05

        return min(base, 1.0)

    def _calculate_visual(
        self,
        item: RawEvidence,
    ) -> float:
        text = " ".join(
            [
                item.title,
                item.claim,
                *item.keywords,
            ]
        ).lower()

        hits = sum(
            1
            for keyword in VISUAL_KEYWORDS
            if keyword.lower() in text
        )

        if hits >= 3:
            return 1.0

        if hits == 2:
            return 0.85

        if hits == 1:
            return 0.70

        return 0.45

    def _duplicate_key(
        self,
        item: RawEvidence,
    ) -> str:
        normalized_claim = re.sub(
            r"[^0-9a-z가-힣]+",
            "",
            item.claim.lower(),
        )

        return normalized_claim[:160]

    def _build_id(
        self,
        item: RawEvidence,
    ) -> str:
        raw_value = (
            f"{item.source_url}|"
            f"{item.claim}"
        )

        digest = hashlib.sha1(
            raw_value.encode("utf-8")
        ).hexdigest()[:12]

        return f"evidence_{digest}"

    @staticmethod
    def _is_valid_url(
        value: str,
    ) -> bool:
        parsed = urlparse(value)

        return (
            parsed.scheme
            in {"http", "https"}
            and bool(parsed.netloc)
        )

    @staticmethod
    def _normalize_text(
        value: str,
    ) -> str:
        return re.sub(
            r"\s+",
            " ",
            value.strip(),
        )

    @staticmethod
    def _deduplicate(
        values: list[str],
    ) -> list[str]:
        result: list[str] = []
        seen: set[str] = set()

        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)

        return result
