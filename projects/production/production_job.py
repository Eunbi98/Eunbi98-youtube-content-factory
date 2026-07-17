from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Callable


class ProductionJobError(ValueError):
    """제작 작업 입력 또는 상태 오류."""


@dataclass(frozen=True)
class ProductionJob:
    version: str
    job_id: str
    episode_id: str
    category: str
    status: str
    created_at: str
    selected_topic: dict[str, Any]
    research_plan: dict[str, Any]
    artifacts: dict[str, str | None]
    next_action: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        return {
            "version": payload["version"],
            "jobId": payload["job_id"],
            "episodeId": payload["episode_id"],
            "category": payload["category"],
            "status": payload["status"],
            "createdAt": payload["created_at"],
            "selectedTopic": payload["selected_topic"],
            "researchPlan": payload["research_plan"],
            "artifacts": payload["artifacts"],
            "nextAction": payload["next_action"],
        }


class ProductionJobPlanner:
    SUPPORTED_CATEGORIES = {
        "mystery",
        "science",
        "history",
        "space",
    }

    def __init__(
        self,
        *,
        now: Callable[[], datetime] | None = None,
    ) -> None:
        self._now = now or (lambda: datetime.now(timezone.utc))

    def select_candidate(
        self,
        candidates_payload: dict[str, Any],
        *,
        rank: int,
    ) -> dict[str, Any]:
        category = str(candidates_payload.get("category") or "").strip().lower()
        if category not in self.SUPPORTED_CATEGORIES:
            raise ProductionJobError(
                f"지원하지 않는 후보 카테고리입니다: {category or '(없음)'}"
            )

        candidates = candidates_payload.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ProductionJobError("주제 후보 목록이 비어 있습니다.")

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if candidate.get("rank") == rank:
                topic = str(candidate.get("topic") or "").strip()
                if not topic:
                    raise ProductionJobError(
                        f"{rank}위 후보의 topic이 비어 있습니다."
                    )
                return candidate

        raise ProductionJobError(f"{rank}위 주제 후보를 찾을 수 없습니다.")

    def create(
        self,
        *,
        episode_id: str,
        category: str,
        candidate: dict[str, Any],
    ) -> ProductionJob:
        normalized_episode_id = episode_id.strip().lower()
        if not re.fullmatch(r"ep\d{3,}", normalized_episode_id):
            raise ProductionJobError(
                "episode_id 형식이 올바르지 않습니다. 예: ep015"
            )

        normalized_category = category.strip().lower()
        if normalized_category not in self.SUPPORTED_CATEGORIES:
            raise ProductionJobError(
                f"지원하지 않는 카테고리입니다: {category}"
            )

        topic = str(candidate.get("topic") or "").strip()
        if not topic:
            raise ProductionJobError("선택한 후보의 topic이 비어 있습니다.")

        now = self._as_utc(self._now())
        created_at = now.isoformat()
        job_id = f"{normalized_episode_id}-{now.strftime('%Y%m%dT%H%M%SZ')}"
        selected_topic = self._normalize_candidate(
            candidate,
            category=normalized_category,
        )

        return ProductionJob(
            version="1.0",
            job_id=job_id,
            episode_id=normalized_episode_id,
            category=normalized_category,
            status="research_planned",
            created_at=created_at,
            selected_topic=selected_topic,
            research_plan=self._build_research_plan(
                category=normalized_category,
                selected_topic=selected_topic,
            ),
            artifacts={
                "evidence": None,
                "episodeSpec": None,
                "timeline": None,
                "video": None,
                "metadata": None,
            },
            next_action="collect_evidence",
        )

    @staticmethod
    def _normalize_candidate(
        candidate: dict[str, Any],
        *,
        category: str,
    ) -> dict[str, Any]:
        sources = candidate.get("sources")
        if not isinstance(sources, list):
            sources = []
        search_queries = candidate.get("search_queries")
        if not isinstance(search_queries, list):
            search_queries = []

        return {
            "rank": int(candidate.get("rank") or 0),
            "category": category,
            "topic": str(candidate.get("topic") or "").strip(),
            "angle": str(candidate.get("angle") or "").strip(),
            "score": float(candidate.get("score") or 0.0),
            "reasons": [
                str(reason).strip()
                for reason in candidate.get("reasons", [])
                if str(reason).strip()
            ],
            "searchQueries": [
                str(query).strip()
                for query in search_queries
                if str(query).strip()
            ],
            "sourceCount": int(candidate.get("source_count") or 0),
            "sources": [
                source for source in sources if isinstance(source, dict)
            ],
        }

    @staticmethod
    def _build_research_plan(
        *,
        category: str,
        selected_topic: dict[str, Any],
    ) -> dict[str, Any]:
        topic = selected_topic["topic"]
        category_question = {
            "mystery": "주장과 확인된 사실은 어디까지 일치하는가?",
            "science": "연구 결과와 아직 검증되지 않은 해석은 무엇인가?",
            "history": "1차 기록과 현대의 해석은 어떻게 다른가?",
            "space": "공식 관측 결과가 실제로 보여주는 것은 무엇인가?",
        }[category]

        queries = list(selected_topic["searchQueries"])
        required_queries = [
            topic,
            f"{topic} official source",
            f"{topic} research paper",
            f"{topic} fact check",
            f"{topic} image archive",
        ]
        for query in required_queries:
            if query not in queries:
                queries.append(query)

        return {
            "topic": topic,
            "angle": selected_topic["angle"],
            "questions": [
                "무엇이 언제 어디에서 발견되거나 발표됐는가?",
                "확인 가능한 핵심 사실과 숫자는 무엇인가?",
                category_question,
                "반대 설명이나 한계는 무엇인가?",
                "영상으로 보여줄 수 있는 장소·유물·관측 자료는 무엇인가?",
                "시청자가 댓글로 답하고 싶어질 마지막 질문은 무엇인가?",
            ],
            "queries": queries,
            "sourcePolicy": {
                "minimumSources": 3,
                "requiredTiers": ["official_or_academic", "reference", "news"],
                "requireCounterpoint": True,
                "rejectUnverifiedFacts": True,
            },
            "sourceSeeds": selected_topic["sources"],
        }

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
