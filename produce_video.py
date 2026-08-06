from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
SUPPORTED_CATEGORIES = ("science", "mystery", "history", "space")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "주제 한 문장으로 조사, 대본, 미디어 수집, TTS, 자막, "
            "Remotion 렌더까지 실행합니다."
        )
    )
    parser.add_argument("topic", help="제작할 영상 주제")
    parser.add_argument(
        "--category",
        choices=SUPPORTED_CATEGORIES,
        default="science",
        help="콘텐츠 카테고리 (기본값: science)",
    )
    parser.add_argument(
        "--episode",
        default="auto",
        help="에피소드 ID 또는 auto (기본값: auto)",
    )
    parser.add_argument(
        "--angle",
        default="",
        help="선택 사항: 영상에서 강조할 관점",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="episode.json과 metadata.json까지만 생성하고 렌더는 생략합니다.",
    )
    parser.add_argument(
        "--skip-typecheck",
        action="store_true",
        help="Remotion TypeScript 검사를 생략합니다.",
    )
    return parser.parse_args()


def run_step(label: str, command: list[str]) -> None:
    print("\n" + "=" * 62)
    print(f"[단계] {label}")
    print("=" * 62)
    completed = subprocess.run(command, cwd=ROOT_DIR, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"{label} 실패 (종료 코드 {completed.returncode})")


def resolve_episode_id(raw_episode: str) -> str:
    if raw_episode.strip().lower() != "auto":
        value = raw_episode.strip().lower()
        if value.startswith("ep") and value[2:].isdigit():
            return f"ep{int(value[2:]):03d}"
        if value.isdigit():
            return f"ep{int(value):03d}"
        raise ValueError("에피소드 형식이 올바르지 않습니다. 예: ep032 또는 auto")

    from projects.production.select_topic import next_episode_id

    return next_episode_id(ROOT_DIR)


def require_generation_environment() -> None:
    if not os.getenv("GITHUB_MODELS_TOKEN"):
        raise RuntimeError(
            "GITHUB_MODELS_TOKEN이 없습니다. GitHub Models 토큰을 환경 변수로 설정하세요."
        )


def build_candidate(topic: str, category: str, angle: str) -> dict:
    normalized_topic = topic.strip()
    if not normalized_topic:
        raise ValueError("주제가 비어 있습니다.")
    return {
        "category": category,
        "candidates": [
            {
                "rank": 1,
                "category": category,
                "topic": normalized_topic,
                "angle": angle.strip(),
                "score": 100,
                "reasons": ["사용자가 직접 선택한 주제"],
                "search_queries": [
                    normalized_topic,
                    f"{normalized_topic} official source",
                    f"{normalized_topic} research paper",
                    f"{normalized_topic} scientific illustration",
                ],
                "source_count": 0,
                "sources": [],
                "preflight_sources": [],
                "preflight_media": {},
            }
        ],
    }


def main() -> int:
    args = parse_args()

    try:
        require_generation_environment()
        episode_id = resolve_episode_id(args.episode)
        episode_dir = ROOT_DIR / "projects" / "episodes" / episode_id
        if episode_dir.exists():
            raise RuntimeError(f"이미 존재하는 에피소드입니다: {episode_id}")
        episode_dir.mkdir(parents=True)

        job_path = episode_dir / "production-job.json"
        evidence_path = episode_dir / "evidence.json"
        episode_path = episode_dir / "episode.json"
        metadata_path = episode_dir / "metadata.json"

        candidate = build_candidate(args.topic, args.category, args.angle)
        with tempfile.TemporaryDirectory(prefix="factory-topic-") as temp_dir:
            candidate_path = Path(temp_dir) / "candidate.json"
            candidate_path.write_text(
                json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            run_step(
                "제작 작업 생성",
                [
                    sys.executable,
                    "projects/production/select_topic.py",
                    "--candidates",
                    str(candidate_path),
                    "--rank",
                    "1",
                    "--episode",
                    episode_id,
                    "--output",
                    str(job_path),
                ],
            )

        run_step(
            "근거 자료 수집과 검증",
            [
                sys.executable,
                "projects/research/collect_evidence.py",
                "--job",
                str(job_path),
                "--output",
                str(evidence_path),
                "--job-output",
                str(job_path),
            ],
        )
        run_step(
            "대본과 업로드 메타데이터 생성",
            [
                sys.executable,
                "projects/production/build_episode_package.py",
                "--job",
                str(job_path),
                "--evidence",
                str(evidence_path),
                "--episode-spec",
                str(episode_path),
                "--metadata",
                str(metadata_path),
                "--job-output",
                str(job_path),
            ],
        )

        if not args.prepare_only:
            factory_command = [
                sys.executable,
                "factory_runner.py",
                "--episode",
                episode_id,
                "--rebuild-timeline",
            ]
            if args.skip_typecheck:
                factory_command.append("--skip-typecheck")
            run_step("미디어 수집과 MP4 렌더", factory_command)

    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"\n[제작 실패] {exc}")
        return 1

    print("\n" + "=" * 62)
    print("영상 제작 완료" if not args.prepare_only else "영상 패키지 준비 완료")
    print(f"에피소드: {episode_id}")
    print(f"주제: {args.topic.strip()}")
    print(f"Episode: {episode_path}")
    print(f"Metadata: {metadata_path}")
    if not args.prepare_only:
        print(f"MP4: {ROOT_DIR / 'projects' / 'output' / f'{episode_id}.mp4'}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
