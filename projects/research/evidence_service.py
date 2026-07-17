from __future__ import annotations

import copy
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


MYSTERY_DIR = Path(__file__).resolve().parents[1] / "plugins" / "mystery"
if str(MYSTERY_DIR) not in sys.path:
    sys.path.insert(0, str(MYSTERY_DIR))

from evidence_collector import EvidenceCollector  # noqa: E402
from evidence_schema import RawEvidence  # noqa: E402


class EvidenceGateError(ValueError):
    """근거 수량, 출처 또는 반대 근거가 기준을 통과하지 못함."""


class EvidenceService:
    def build_evidence(
        self,
        *,
        topic: str,
        provider_result: dict[str, Any],
    ) -> dict[str, Any]:
        if provider_result.get("status") != "complete":
            raise EvidenceGateError(
                "Provider가 충분한 근거를 수집하지 못했습니다."
            )
        raw_items = provider_result.get("items")
        if not isinstance(raw_items, list):
            raise EvidenceGateError("Evidence items가 배열이 아닙니다.")

        converted = [self._to_raw_evidence(item) for item in raw_items]
        result = EvidenceCollector().collect(
            topic=topic,
            raw_items=converted,
        )
        self._validate_gate(result.to_dict())

        payload = result.to_dict()
        payload.update(
            {
                "status": "verified",
                "summary": str(provider_result.get("summary") or "").strip(),
                "uncertainties": provider_result.get("uncertainties", []),
                "citations": provider_result.get("citations", []),
                "provider": provider_result.get("provider"),
                "model": provider_result.get("model"),
                "verified_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return payload

    @staticmethod
    def advance_job(
        job_payload: dict[str, Any],
        *,
        evidence_path: str,
    ) -> dict[str, Any]:
        if job_payload.get("status") != "research_planned":
            raise EvidenceGateError(
                "research_planned 상태의 작업만 evidence_ready로 전환할 수 있습니다."
            )
        updated = copy.deepcopy(job_payload)
        artifacts = updated.get("artifacts")
        if not isinstance(artifacts, dict):
            artifacts = {}
            updated["artifacts"] = artifacts
        artifacts["evidence"] = evidence_path
        updated["status"] = "evidence_ready"
        updated["nextAction"] = "build_episode_spec"
        updated["updatedAt"] = datetime.now(timezone.utc).isoformat()
        return updated

    @staticmethod
    def _to_raw_evidence(item: Any) -> RawEvidence:
        if not isinstance(item, dict):
            raise EvidenceGateError("Evidence item은 객체여야 합니다.")
        return RawEvidence(
            title=str(item.get("title") or ""),
            claim=str(item.get("claim") or ""),
            source_name=str(item.get("source_name") or ""),
            source_url=str(item.get("source_url") or ""),
            source_tier=str(item.get("source_tier") or "unknown"),
            evidence_type=str(item.get("evidence_type") or "fact"),
            published_at=str(item.get("published_at") or "") or None,
            keywords=[
                str(keyword)
                for keyword in item.get("keywords", [])
                if str(keyword).strip()
            ],
        )

    @staticmethod
    def _validate_gate(payload: dict[str, Any]) -> None:
        items = payload.get("items")
        if not isinstance(items, list) or len(items) < 3:
            raise EvidenceGateError("검증된 Evidence가 최소 3개 필요합니다.")

        domains = {
            urlparse(str(item.get("source_url") or "")).netloc.casefold()
            for item in items
            if isinstance(item, dict)
        }
        domains.discard("")
        if len(domains) < 3:
            raise EvidenceGateError("서로 다른 출처 도메인이 최소 3개 필요합니다.")

        if not any(
            item.get("source_tier") in {"official", "academic"}
            for item in items
            if isinstance(item, dict)
        ):
            raise EvidenceGateError("공식 또는 학술 출처가 최소 1개 필요합니다.")

        if not any(
            item.get("evidence_type") == "counterpoint"
            for item in items
            if isinstance(item, dict)
        ):
            raise EvidenceGateError("반대 근거나 불확실성 Evidence가 필요합니다.")
