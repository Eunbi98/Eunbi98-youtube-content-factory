from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


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
            "생략하면 무료 공개 자료와 GitHub Models로 근거를 수집합니다."
        ),
    )
    parser.add_argument(
        "--job-output",
        type=Path,
        help="갱신할 Production Job 경로. 생략하면 입력 Job을 갱신합니다.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        job_payload = json.loads(args.job.read_text(encoding="utf-8"))
        if not isinstance(job_payload, dict):
            raise EvidenceGateError("Production Job 최상위 값은 객체여야 합니다.")

        if args.provider_result:
            provider_result = json.loads(
                args.provider_result.read_text(encoding="utf-8")
            )
            if not isinstance(provider_result, dict):
                raise EvidenceGateError("Provider 결과 최상위 값은 객체여야 합니다.")
        else:
            provider = GithubModelsEvidenceProvider.from_environment()
            provider_result = provider.collect(job_payload)
        topic = str(job_payload["selectedTopic"]["topic"])
        service = EvidenceService()
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
