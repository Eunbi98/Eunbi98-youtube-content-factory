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
        selected_topic = job_payload["selectedTopic"]
        preflight_sources = selected_topic.get("preflightSources")
        if isinstance(preflight_sources, list) and preflight_sources:
            sources = [
                source for source in preflight_sources if isinstance(source, dict)
            ]
            search_queries = [
                str(query).strip()
                for query in selected_topic.get("searchQueries", [])
                if str(query).strip()
            ]
        else:
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
            "Use only the supplied sourceDocuments. Return 2 to 5 non-duplicate "
            "evidence items from at least 2 source domains, including at least one "
            "official or academic source. Include either a counterpoint evidence "
            "item or a concrete uncertainty in the uncertainties array. "
            "Every claim must be directly supported by the text of its selected "
            "source document. Copy source_url, source_name, source_tier, and "
            "published_at exactly from that document. Never invent facts, URLs, "
            "dates, numbers, or quotations. If the documents are insufficient, "
            "return status insufficient. Write claims and summary in Korean."
        )
        user_payload = {
            "episodeId": job_payload["episodeId"],
            "category": job_payload["category"],
            "topic": job_payload["selectedTopic"]["topic"],
            "angle": job_payload["selectedTopic"].get("angle", ""),
            "questions": job_payload["researchPlan"].get("questions", []),
            "sourceDocuments": sources,
        }
        result = self._request_evidence(system=system, user_payload=user_payload)
        self._validate_result_sources(result, sources)
        coverage_issues = self._coverage_issues(result)
        if coverage_issues:
            retry_system = (
                system
                + " The previous selection failed these mandatory checks: "
                + "; ".join(coverage_issues)
                + ". Retry once. Select at least two items whose source_url hostnames "
                "are different. Include an official or academic item and either a "
                "counterpoint or a concrete uncertainty. Use only supplied documents "
                "and do not weaken any claim."
            )
            result = self._request_evidence(
                system=retry_system,
                user_payload=user_payload,
            )
            self._validate_result_sources(result, sources)
            coverage_issues = self._coverage_issues(result)
            if coverage_issues:
                raise EvidenceProviderError(
                    "근거 재선정 후에도 제작 품질 기준을 충족하지 못했습니다: "
                    + ", ".join(coverage_issues)
                )
        result["citations"] = [
            {"title": item["title"], "url": item["source_url"]}
            for item in sources
        ]
        result["provider"] = "github_models_public_sources"
        result["model"] = self._client.model
        result["search_queries"] = search_queries
        return result

    def _request_evidence(
        self,
        *,
        system: str,
        user_payload: dict[str, Any],
    ) -> dict[str, Any]:
        try:
            return self._client.complete_json(
                system=system,
                user_payload=user_payload,
                schema_name="factory_evidence_result",
                schema=EVIDENCE_SCHEMA,
            )
        except GithubModelsError as exc:
            raise EvidenceProviderError(str(exc)) from exc

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
                    "plannedQueries": job_payload["researchPlan"].get("queries", []),
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
    def _coverage_issues(result: dict[str, Any]) -> list[str]:
        items = result.get("items")
        if not isinstance(items, list):
            return ["Evidence items가 배열이 아님"]
        valid_items = [item for item in items if isinstance(item, dict)]
        issues: list[str] = []
        if result.get("status") != "complete":
            issues.append("수집 상태가 complete가 아님")
        if len(valid_items) < 2:
            issues.append("검증 근거 2개 미만")
        domains = {
            urlparse(str(item.get("source_url") or "")).netloc.casefold()
            for item in valid_items
        }
        domains.discard("")
        if len(domains) < 2:
            issues.append("서로 다른 출처 도메인 2개 미만")
        if not any(
            item.get("source_tier") in {"official", "academic"}
            for item in valid_items
        ):
            issues.append("공식 또는 학술 출처 없음")
        has_counterpoint = any(
            item.get("evidence_type") == "counterpoint"
            for item in valid_items
        )
        uncertainties = result.get("uncertainties")
        has_uncertainty = isinstance(uncertainties, list) and any(
            str(value).strip() for value in uncertainties
        )
        if not has_counterpoint and not has_uncertainty:
            issues.append("반대 근거나 명시적 불확실성 없음")
        return issues

    @staticmethod
    def _validate_source_pool(sources: list[dict[str, str]]) -> None:
        domains = {
            urlparse(str(source.get("source_url") or "")).netloc.casefold()
            for source in sources
        }
        domains.discard("")
        if len(sources) < 2 or len(domains) < 2:
            raise EvidenceProviderError(
                "무료 공개 자료에서 서로 다른 출처 2곳을 확보하지 못했습니다. "
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
