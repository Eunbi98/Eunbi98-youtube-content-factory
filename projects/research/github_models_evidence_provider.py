from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from projects.ai.github_models_client import GithubModelsClient, GithubModelsError
from projects.research.openai_evidence_provider import EVIDENCE_SCHEMA
from projects.research.public_source_collector import (
    PublicSourceCollector,
    PublicSourceError,
)


class EvidenceProviderError(RuntimeError):
    """무료 근거 수집 또는 GitHub Models 분석 오류."""


SEARCH_QUERY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "englishTopic": {"type": "string"},
        "queries": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4,
        },
    },
    "required": ["englishTopic", "queries"],
    "additionalProperties": False,
}


class GithubModelsEvidenceProvider:
    def __init__(
        self,
        *,
        client: GithubModelsClient,
        source_collector: PublicSourceCollector | None = None,
    ) -> None:
        self._client = client
        self._source_collector = source_collector or PublicSourceCollector()

    @classmethod
    def from_environment(cls) -> "GithubModelsEvidenceProvider":
        return cls(client=GithubModelsClient.from_environment())

    def collect(self, job_payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_job(job_payload)
        search_queries = self._expand_search_queries(job_payload)
        try:
            sources = self._source_collector.collect(
                job_payload,
                search_queries=search_queries,
            )
        except PublicSourceError as exc:
            raise EvidenceProviderError(str(exc)) from exc
        self._validate_source_pool(sources)

        system = (
            "You verify source documents for a Korean educational YouTube Short. "
            "Use only the supplied sourceDocuments. Return 3 to 6 non-duplicate "
            "evidence items from at least 3 source domains, including at least one "
            "official or academic source and one counterpoint or explicit limit. "
            "Every claim must be directly supported by the text of its selected "
            "source document. Copy source_url, source_name, source_tier, and "
            "published_at exactly from that document. Never invent facts, URLs, "
            "dates, numbers, or quotations. If the documents are insufficient, "
            "return status insufficient. Write claims and summary in Korean."
        )
        try:
            result = self._client.complete_json(
                system=system,
                user_payload={
                    "episodeId": job_payload["episodeId"],
                    "category": job_payload["category"],
                    "topic": job_payload["selectedTopic"]["topic"],
                    "angle": job_payload["selectedTopic"].get("angle", ""),
                    "questions": job_payload["researchPlan"].get("questions", []),
                    "sourceDocuments": sources,
                },
                schema_name="factory_evidence_result",
                schema=EVIDENCE_SCHEMA,
            )
        except GithubModelsError as exc:
            raise EvidenceProviderError(str(exc)) from exc
        self._validate_result_sources(result, sources)
        result["citations"] = [
            {"title": item["title"], "url": item["source_url"]}
            for item in sources
        ]
        result["provider"] = "github_models_public_sources"
        result["model"] = self._client.model
        return result

    def _expand_search_queries(self, job_payload: dict[str, Any]) -> list[str]:
        topic = str(job_payload["selectedTopic"]["topic"])
        system = (
            "Convert the Korean video topic into concise English search terms. "
            "Do not research, answer the topic, or add factual claims. Return one "
            "canonical English topic name and 2 to 4 search queries suitable for "
            "English Wikipedia and scholarly indexes. Preserve named entities."
        )
        try:
            result = self._client.complete_json(
                system=system,
                user_payload={
                    "topic": topic,
                    "category": job_payload["category"],
                },
                schema_name="factory_research_queries",
                schema=SEARCH_QUERY_SCHEMA,
                max_tokens=400,
            )
        except GithubModelsError as exc:
            raise EvidenceProviderError(str(exc)) from exc
        values = [
            str(result.get("englishTopic") or "").strip(),
            *[
                str(query).strip()
                for query in result.get("queries", [])
                if str(query).strip()
            ],
        ]
        queries = list(dict.fromkeys(value for value in values if value))
        if len(queries) < 2:
            raise EvidenceProviderError(
                "GitHub Models가 영어 자료 검색어를 충분히 만들지 못했습니다."
            )
        return queries

    @staticmethod
    def _validate_source_pool(sources: list[dict[str, str]]) -> None:
        domains = {
            urlparse(str(source.get("source_url") or "")).netloc.casefold()
            for source in sources
        }
        domains.discard("")
        if len(sources) < 3 or len(domains) < 3:
            raise EvidenceProviderError(
                "무료 공개 자료에서 서로 다른 출처 3곳을 확보하지 못했습니다. "
                f"수집 문서: {len(sources)}, 도메인: {len(domains)}"
            )
        if not any(
            source.get("source_tier") in {"official", "academic"}
            for source in sources
        ):
            raise EvidenceProviderError(
                "무료 공개 자료에서 공식 또는 학술 출처를 확보하지 못했습니다."
            )

    @staticmethod
    def _validate_result_sources(
        result: dict[str, Any],
        sources: list[dict[str, str]],
    ) -> None:
        allowed = {
            source["source_url"]: source
            for source in sources
            if source.get("source_url")
        }
        items = result.get("items")
        if not isinstance(items, list):
            raise EvidenceProviderError("Evidence 결과 items가 배열이 아닙니다.")
        for item in items:
            if not isinstance(item, dict):
                raise EvidenceProviderError("Evidence item 형식이 잘못됐습니다.")
            url = str(item.get("source_url") or "")
            source = allowed.get(url)
            if source is None:
                raise EvidenceProviderError(
                    "GitHub Models가 수집하지 않은 출처 URL을 반환했습니다."
                )
            for field in ("source_name", "source_tier", "published_at"):
                if str(item.get(field) or "") != str(source.get(field) or ""):
                    raise EvidenceProviderError(
                        f"Evidence의 {field}가 원본 공개 자료와 다릅니다."
                    )

    @staticmethod
    def _validate_job(job_payload: dict[str, Any]) -> None:
        if job_payload.get("status") != "research_planned":
            raise EvidenceProviderError(
                "Evidence 수집은 research_planned 상태에서만 가능합니다."
            )
        if not isinstance(job_payload.get("selectedTopic"), dict):
            raise EvidenceProviderError("Production Job의 selectedTopic이 없습니다.")
        if not isinstance(job_payload.get("researchPlan"), dict):
            raise EvidenceProviderError("Production Job의 researchPlan이 없습니다.")
