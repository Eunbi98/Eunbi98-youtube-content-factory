from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.production.episode_quality import (  # noqa: E402
    EpisodeQualityError,
    EpisodeQualityService,
)
from projects.production.github_models_episode_provider import (  # noqa: E402
    EpisodeProviderError,
    GithubModelsEpisodeProvider,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="검증된 Evidence로 Episode와 업로드 메타데이터를 생성합니다."
    )
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--episode-spec", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--provider-result", type=Path)
    parser.add_argument("--job-output", type=Path)
    return parser.parse_args()


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise EpisodeProviderError(f"최상위 값은 객체여야 합니다: {path}")
    return payload


def main() -> int:
    args = parse_args()
    try:
        job_payload = _load(args.job)
        evidence_payload = _load(args.evidence)
        if args.provider_result:
            package = _load(args.provider_result)
        else:
            package = GithubModelsEpisodeProvider.from_environment().build(
                job_payload=job_payload,
                evidence_payload=evidence_payload,
            )
        episode_payload = package["episode"]
        metadata_payload = package["metadata"]
        if not isinstance(episode_payload, dict) or not isinstance(
            metadata_payload, dict
        ):
            raise EpisodeProviderError("episode 또는 metadata 형식이 잘못됐습니다.")

        args.episode_spec.parent.mkdir(parents=True, exist_ok=True)
        args.metadata.parent.mkdir(parents=True, exist_ok=True)
        args.episode_spec.write_text(
            json.dumps(episode_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        args.metadata.write_text(
            json.dumps(metadata_payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

        updated_job = EpisodeQualityService().validate_and_advance(
            job_payload=job_payload,
            evidence_payload=evidence_payload,
            episode_spec_path=args.episode_spec,
            metadata_payload=metadata_payload,
            metadata_path=args.metadata,
        )
    except (
        OSError,
        json.JSONDecodeError,
        KeyError,
        EpisodeProviderError,
        EpisodeQualityError,
    ) as exc:
        print(f"[실패] {exc}")
        return 2

    job_output = args.job_output or args.job
    job_output.parent.mkdir(parents=True, exist_ok=True)
    job_output.write_text(
        json.dumps(updated_job, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Episode 및 업로드 메타데이터 생성 완료")
    print(f"Episode: {args.episode_spec}")
    print(f"Metadata: {args.metadata}")
    print(f"Production Job: {job_output}")
    print("상태: episode_ready")
    print("다음 단계: build_timeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
