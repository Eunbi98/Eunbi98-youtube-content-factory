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
    TimelineQualityService,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Timeline과 미디어 검색어를 검증합니다."
    )
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--media-queries", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        job_payload = json.loads(args.job.read_text(encoding="utf-8"))
        if not isinstance(job_payload, dict):
            raise EpisodeQualityError("Production Job 최상위 값은 객체여야 합니다.")
        updated_job = TimelineQualityService().validate_and_advance(
            job_payload=job_payload,
            timeline_path=args.timeline,
            media_queries_path=args.media_queries,
        )
    except (OSError, json.JSONDecodeError, EpisodeQualityError) as exc:
        print(f"[실패] {exc}")
        return 2

    args.job.write_text(
        json.dumps(updated_job, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print("Timeline 및 미디어 검색어 품질 검사 완료")
    print("상태: media_planned")
    print("다음 단계: collect_media")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
