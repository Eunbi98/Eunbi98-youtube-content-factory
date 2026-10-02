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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Episode 명세와 업로드 메타데이터를 검증합니다."
    )
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--episode-spec", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    return parser.parse_args()


def _load(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise EpisodeQualityError(f"최상위 값은 객체여야 합니다: {path}")
    return payload


def main() -> int:
    args = parse_args()
    try:
        job_payload = _load(args.job)
        evidence_payload = _load(args.evidence)
        metadata_payload = _load(args.metadata)
        updated_job = EpisodeQualityService().validate_and_advance(
            job_payload=job_payload,
            evidence_payload=evidence_payload,
            episode_spec_path=args.episode_spec,
            metadata_payload=metadata_payload,
            metadata_path=args.metadata,
        )
    except (OSError, json.JSONDecodeError, EpisodeQualityError) as exc:
        print(f"[실패] {exc}")
        return 2

    args.job.write_text(
        json.dumps(updated_job, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Episode 품질 검사 완료")
    print("상태: episode_ready")
    print("다음 단계: build_timeline")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
