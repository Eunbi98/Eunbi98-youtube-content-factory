from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.production.production_job import (  # noqa: E402
    ProductionJobError,
    ProductionJobPlanner,
)


def next_episode_id(root_dir: Path) -> str:
    numbers = []
    episodes_dir = root_dir / "projects" / "episodes"
    for episode_dir in episodes_dir.glob("ep*"):
        match = re.fullmatch(r"ep(\d+)", episode_dir.name.lower())
        if match:
            numbers.append(int(match.group(1)))
    return f"ep{max(numbers, default=0) + 1:03d}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Auto Topic Finder 후보를 제작 작업으로 확정합니다."
    )
    parser.add_argument(
        "--candidates",
        type=Path,
        required=True,
        help="Auto Topic Finder 결과 JSON",
    )
    parser.add_argument(
        "--rank",
        type=int,
        default=1,
        help="선택할 후보 순위 (기본값: 1)",
    )
    parser.add_argument(
        "--episode",
        default="auto",
        help="에피소드 ID 또는 auto (기본값: auto)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Production Job 출력 JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        payload = json.loads(args.candidates.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ProductionJobError("후보 JSON 최상위 값은 객체여야 합니다.")

        planner = ProductionJobPlanner()
        candidate = planner.select_candidate(payload, rank=args.rank)
        episode_id = (
            next_episode_id(ROOT_DIR)
            if args.episode.strip().lower() == "auto"
            else args.episode
        )
        job = planner.create(
            episode_id=episode_id,
            category=str(payload.get("category") or ""),
            candidate=candidate,
        )
    except (OSError, json.JSONDecodeError, ProductionJobError) as exc:
        print(f"[실패] {exc}")
        return 2

    output_path = args.output or (
        ROOT_DIR / "projects" / "output" / "jobs" / f"{job.episode_id}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(job.to_dict(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("Production Job 생성 완료")
    print(f"작업: {job.job_id}")
    print(f"에피소드: {job.episode_id}")
    print(f"선택 주제: {job.selected_topic['topic']}")
    print(f"상태: {job.status}")
    print(f"다음 단계: {job.next_action}")
    print(f"출력: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
