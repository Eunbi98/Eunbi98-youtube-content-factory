from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

MEDIA_DIR = ROOT_DIR / "projects" / "media"
PROVIDERS_DIR = MEDIA_DIR / "providers"
for module_path in (MEDIA_DIR, PROVIDERS_DIR):
    if str(module_path) not in sys.path:
        sys.path.insert(0, str(module_path))

from projects.production.production_job import ProductionJobPlanner  # noqa: E402
from projects.ai.github_models_client import GithubModelsClient  # noqa: E402
from projects.research.evidence_service import (  # noqa: E402
    EvidenceGateError,
    EvidenceService,
)
from projects.research.github_models_evidence_provider import (  # noqa: E402
    EvidenceProviderError,
    GithubModelsEvidenceProvider,
)
from projects.research.public_source_collector import PublicSourceCollector  # noqa: E402
from provider_models import MediaCandidate  # noqa: E402


class TopicPreflightError(RuntimeError):
    """주제 후보 사전 검증 입력 또는 실행 오류."""


class CandidatePreflightService:
    def __init__(
        self,
        *,
        evidence_provider: Any | None = None,
        evidence_service: EvidenceService | None = None,
        media_providers: dict[str, Any] | None = None,
        minimum_media_candidates: int = 5,
        minimum_media_queries: int = 2,
        maximum_candidates_checked: int = 5,
    ) -> None:
        self._evidence_provider = evidence_provider or GithubModelsEvidenceProvider(
            client=GithubModelsClient.from_environment(timeout_seconds=60.0),
            source_collector=PublicSourceCollector(timeout_seconds=8.0),
        )
        self._evidence_service = evidence_service or EvidenceService()
        if media_providers is None:
            from providers.nasa_provider import NasaProvider
            from providers.openverse_provider import OpenverseProvider
            from providers.wikimedia_provider import WikimediaProvider

            media_providers = {
                "openverse": OpenverseProvider(timeout_seconds=8.0),
                "wikimedia": WikimediaProvider(timeout_seconds=8.0),
                "nasa": NasaProvider(timeout_seconds=8.0),
            }
        self._media_providers = media_providers
        self._minimum_media_candidates = minimum_media_candidates
        self._minimum_media_queries = minimum_media_queries
        self._maximum_candidates_checked = maximum_candidates_checked

    def filter_payload(
        self,
        payload: dict[str, Any],
        *,
        limit: int,
    ) -> dict[str, Any]:
        raw_candidates = payload.get("candidates")
        if not isinstance(raw_candidates, list):
            raise TopicPreflightError("주제 후보 목록이 배열이 아닙니다.")
        if limit < 1:
            raise TopicPreflightError("사전 검증 후보 수는 1개 이상이어야 합니다.")

        accepted: list[dict[str, Any]] = []
        rejected: list[dict[str, str]] = []
        checked = 0
        for raw_candidate in raw_candidates:
            if checked >= self._maximum_candidates_checked:
                break
            if not isinstance(raw_candidate, dict):
                continue
            checked += 1
            try:
                accepted.append(self._preflight_candidate(raw_candidate))
            except (EvidenceProviderError, EvidenceGateError, TopicPreflightError) as exc:
                rejected.append(
                    {
                        "topic": str(raw_candidate.get("topic") or "(제목 없음)"),
                        "reason": str(exc),
                    }
                )
            if len(accepted) >= limit:
                break

        for rank, candidate in enumerate(accepted, start=1):
            candidate["rank"] = rank

        result = dict(payload)
        result["candidates"] = accepted
        result["candidate_count"] = len(accepted)
        result["mode"] = f"{payload.get('mode') or 'unknown'}+preflight"
        result["preflight"] = {
            "checked": checked,
            "accepted": len(accepted),
            "rejected": rejected,
            "evidencePolicy": {
                "minimumDomains": 2,
                "requireOfficialOrAcademic": True,
                "requireCounterpointOrUncertainty": True,
            },
            "mediaPolicy": {
                "minimumCandidates": self._minimum_media_candidates,
                "minimumSuccessfulQueries": self._minimum_media_queries,
                "providers": list(self._media_providers),
            },
        }
        warnings = result.get("warnings")
        if not isinstance(warnings, list):
            warnings = []
        if rejected:
            warnings.append(
                f"자료·이미지 사전 검증에서 후보 {len(rejected)}개를 제외했습니다."
            )
        result["warnings"] = warnings
        return result

    def _preflight_candidate(self, candidate: dict[str, Any]) -> dict[str, Any]:
        category = str(candidate.get("category") or "").strip().lower()
        if category not in ProductionJobPlanner.SUPPORTED_CATEGORIES:
            raise TopicPreflightError(f"지원하지 않는 카테고리입니다: {category}")
        topic = str(candidate.get("topic") or "").strip()
        if not topic:
            raise TopicPreflightError("주제 제목이 비어 있습니다.")

        job = ProductionJobPlanner().create(
            episode_id="ep000",
            category=category,
            candidate=candidate,
        ).to_dict()
        provider_result = self._evidence_provider.collect(job)
        evidence = self._evidence_service.build_evidence(
            topic=topic,
            provider_result=provider_result,
        )
        evidence = self._compact_evidence(evidence)

        search_queries = self._media_queries(candidate, provider_result)
        media_preflight = self._probe_media(
            category=category,
            queries=search_queries,
        )

        items = evidence.get("items", [])
        domains = {
            urlparse(str(item.get("source_url") or "")).netloc.casefold()
            for item in items
            if isinstance(item, dict)
        }
        domains.discard("")
        authoritative = sum(
            item.get("source_tier") in {"official", "academic"}
            for item in items
            if isinstance(item, dict)
        )

        result = dict(candidate)
        result["production_ready"] = True
        result["readiness_score"] = 100
        result["preflight_evidence"] = evidence
        result["preflight_media"] = media_preflight
        result["evidence_preflight"] = {
            "item_count": len(items),
            "domain_count": len(domains),
            "authoritative_count": authoritative,
        }
        result["media_preflight"] = {
            "candidate_count": media_preflight["candidateCount"],
            "successful_query_count": media_preflight["successfulQueryCount"],
            "providers": media_preflight["providers"],
        }
        checks = [
            str(value)
            for value in result.get("readiness_checks", [])
            if str(value).strip()
        ]
        checks.extend(
            [
                f"검증 본문 {len(items)}건·독립 출처 {len(domains)}곳 확보",
                f"저작권 사용 가능한 이미지 후보 {media_preflight['candidateCount']}개 확보",
                "자료와 이미지 사전 패키지 저장 완료",
            ]
        )
        result["readiness_checks"] = list(dict.fromkeys(checks))
        return result

    def _probe_media(
        self,
        *,
        category: str,
        queries: list[str],
    ) -> dict[str, Any]:
        unique: dict[tuple[str, str], MediaCandidate] = {}
        successful_queries = 0
        provider_counts: Counter[str] = Counter()
        used_queries: list[str] = []

        for query in queries[:4]:
            before = len(unique)
            provider_names = ["openverse", "wikimedia"]
            if category == "space":
                provider_names.append("nasa")
            for provider_name in provider_names:
                provider = self._media_providers.get(provider_name)
                if provider is None:
                    continue
                try:
                    candidates = provider.search(query=query, limit=12)
                except Exception:
                    continue
                for media in candidates:
                    if not isinstance(media, MediaCandidate):
                        continue
                    if media.width < 720 or media.height < 720:
                        continue
                    key = (media.provider, media.media_id)
                    if key in unique:
                        continue
                    unique[key] = media
                    provider_counts[media.provider] += 1
            if len(unique) > before:
                successful_queries += 1
                used_queries.append(query)
            if (
                len(unique) >= self._minimum_media_candidates
                and successful_queries >= self._minimum_media_queries
            ):
                break

        if len(unique) < self._minimum_media_candidates:
            raise TopicPreflightError(
                "저작권 사용 가능한 이미지 후보를 충분히 확보하지 못했습니다. "
                f"확보: {len(unique)}개, 필요: {self._minimum_media_candidates}개"
            )
        if successful_queries < self._minimum_media_queries:
            raise TopicPreflightError(
                "서로 다른 장면용 이미지 검색어가 부족합니다. "
                f"성공 검색어: {successful_queries}개"
            )

        samples = [
            {
                "provider": media.provider,
                "mediaId": media.media_id,
                "title": media.title,
                "sourceUrl": media.source_url,
                "license": media.license_name,
                "width": media.width,
                "height": media.height,
            }
            for media in list(unique.values())[:5]
        ]
        return {
            "status": "verified",
            "candidateCount": len(unique),
            "successfulQueryCount": successful_queries,
            "queries": used_queries,
            "providers": dict(provider_counts),
            "samples": samples,
        }

    @staticmethod
    def _media_queries(
        candidate: dict[str, Any],
        provider_result: dict[str, Any],
    ) -> list[str]:
        values = [
            *provider_result.get("search_queries", []),
            *candidate.get("search_queries", []),
            str(candidate.get("topic") or ""),
        ]
        return list(
            dict.fromkeys(
                str(value).strip()
                for value in values
                if str(value).strip()
            )
        )

    @staticmethod
    def _compact_evidence(evidence: dict[str, Any]) -> dict[str, Any]:
        result = dict(evidence)
        items = [
            item for item in result.get("items", []) if isinstance(item, dict)
        ]
        result["items"] = items[:5]
        result["citations"] = [
            {
                "title": str(item.get("title") or ""),
                "url": str(item.get("source_url") or ""),
            }
            for item in result["items"]
        ]
        return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="실제 근거와 이미지가 확보된 주제 후보만 남깁니다."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise TopicPreflightError("주제 후보 파일 최상위 값은 객체여야 합니다.")
        result = CandidatePreflightService().filter_payload(
            payload,
            limit=min(5, max(1, args.limit)),
        )
    except (
        OSError,
        json.JSONDecodeError,
        EvidenceProviderError,
        EvidenceGateError,
        TopicPreflightError,
    ) as exc:
        print(f"[실패] {exc}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Topic Preflight 완료")
    print(f"검사: {result['preflight']['checked']}개")
    print(f"통과: {result['candidate_count']}개")
    print(f"출력: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
