from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.research.evidence_service import (  # noqa: E402
    EvidenceGateError,
    EvidenceService,
)
from projects.research.github_models_evidence_provider import (  # noqa: E402
    EvidenceProviderError,
    GithubModelsEvidenceProvider,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Production Job의 실제 웹 근거를 수집하고 검증합니다."
    )
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--provider-result",
        type=Path,
        help=(
            "저장된 Provider 결과를 재검증합니다. "
            "생략하면 사전 검증 자료를 우선 재사용하고, 없을 때만 "
            "무료 공개 자료와 GitHub Models로 근거를 수집합니다."
        ),
    )
    parser.add_argument(
        "--job-output",
        type=Path,
        help="갱신할 Production Job 경로. 생략하면 입력 Job을 갱신합니다.",
    )
    return parser.parse_args()


def _text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def evidence_from_preflight_sources(
    *,
    topic: str,
    sources: list[dict[str, Any]],
    service: EvidenceService,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        claim = _text(source.get("text") or source.get("claim"))
        title = _text(source.get("title"))
        source_url = _text(source.get("source_url") or source.get("url"))
        if not title or not claim or not source_url:
            continue
        words = [
            word.strip(".,:;!?()[]{}\"'")
            for word in title.split()
            if len(word.strip(".,:;!?()[]{}\"'")) >= 2
        ]
        items.append(
            {
                "title": title,
                "claim": claim[:1600],
                "source_name": _text(source.get("source_name") or source.get("source")) or title,
                "source_url": source_url,
                "source_tier": _text(source.get("source_tier")) or "reference",
                "evidence_type": "fact",
                "published_at": _text(source.get("published_at")) or None,
                "keywords": words[:8] or [topic],
            }
        )

    if len(items) < 2:
        raise EvidenceGateError(
            "사전 검증 자료 본문이 최소 2개 필요합니다."
        )

    summary_parts = [item["claim"] for item in items[:3]]
    provider_result = {
        "status": "complete",
        "summary": " ".join(summary_parts)[:2400],
        "uncertainties": [
            "사전 검증 자료가 확인한 사실 이외의 세부 해석은 확정하지 않습니다."
        ],
        "items": items,
        "citations": [
            {"title": item["title"], "url": item["source_url"]}
            for item in items
        ],
        "provider": "topic_preflight",
        "model": None,
    }
    return service.build_evidence(
        topic=topic,
        provider_result=provider_result,
    )


def main() -> int:
    args = parse_args()
    try:
        job_payload = json.loads(args.job.read_text(encoding="utf-8"))
        if not isinstance(job_payload, dict):
            raise EvidenceGateError("Production Job 최상위 값은 객체여야 합니다.")

        selected_topic = job_payload.get("selectedTopic")
        preflight_evidence = (
            selected_topic.get("preflightEvidence")
            if isinstance(selected_topic, dict)
            else None
        )
        preflight_sources = (
            selected_topic.get("preflightSources")
            if isinstance(selected_topic, dict)
            else None
        )
        service = EvidenceService()
        if isinstance(preflight_evidence, dict) and preflight_evidence:
            service.validate_verified_evidence(preflight_evidence)
            evidence = preflight_evidence
        elif isinstance(preflight_sources, list) and preflight_sources:
            topic = str(selected_topic.get("topic") or "")
            evidence = evidence_from_preflight_sources(
                topic=topic,
                sources=preflight_sources,
                service=service,
            )
        elif args.provider_result:
            provider_result = json.loads(
                args.provider_result.read_text(encoding="utf-8")
            )
            if not isinstance(provider_result, dict):
                raise EvidenceGateError("Provider 결과 최상위 값은 객체여야 합니다.")
            topic = str(job_payload["selectedTopic"]["topic"])
            evidence = service.build_evidence(
                topic=topic,
                provider_result=provider_result,
            )
        else:
            provider = GithubModelsEvidenceProvider.from_environment()
            provider_result = provider.collect(job_payload)
            topic = str(job_payload["selectedTopic"]["topic"])
            evidence = service.build_evidence(
                topic=topic,
                provider_result=provider_result,
            )
        updated_job = service.advance_job(
            job_payload,
            evidence_path=args.output.as_posix(),
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        EvidenceProviderError,
        EvidenceGateError,
    ) as exc:
        print(f"[실패] {exc}")
        return 2

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    job_output = args.job_output or args.job
    job_output.parent.mkdir(parents=True, exist_ok=True)
    job_output.write_text(
        json.dumps(updated_job, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Evidence 수집 및 검증 완료")
    print(f"Evidence: {args.output}")
    print(f"Production Job: {job_output}")
    print("상태: evidence_ready")
    print("다음 단계: build_episode_spec")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
