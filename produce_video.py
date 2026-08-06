from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from difflib import SequenceMatcher
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parent
SUPPORTED_CATEGORIES = ("science", "mystery", "history", "space")

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.topic.topic_preflight import (  # noqa: E402
    CandidatePreflightService,
    TopicPreflightError,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "주제 한 문장으로 중복검사, 자료·미디어 사전검증, 로컬 대본 생성, "
            "TTS, 자막, Remotion 렌더까지 실행합니다."
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
    parser.add_argument(
        "--allow-similar-topic",
        action="store_true",
        help="기존 주제와 유사해도 강제로 제작합니다.",
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


def normalize_topic(value: str) -> str:
    normalized = re.sub(r"[\s\W_]+", "", value.strip().lower(), flags=re.UNICODE)
    replacements = {
        "세개": "3개",
        "두개": "2개",
        "한개": "1개",
        "진짜이유": "이유",
        "이유는무엇일까": "이유",
        "왜그럴까": "왜",
    }
    for old, new in replacements.items():
        normalized = normalized.replace(old, new)
    return normalized


def known_topics() -> list[tuple[str, str]]:
    topics: list[tuple[str, str]] = []
    published_path = ROOT_DIR / "config" / "published_topics.json"
    if published_path.exists():
        try:
            payload = json.loads(published_path.read_text(encoding="utf-8"))
            for value in payload.get("topics", []):
                topic = str(value).strip()
                if topic:
                    topics.append((topic, "config/published_topics.json"))
        except (OSError, json.JSONDecodeError, AttributeError):
            pass

    for episode_path in (ROOT_DIR / "projects" / "episodes").glob("ep*/episode.json"):
        try:
            payload = json.loads(episode_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        title = str(payload.get("title") or "").strip()
        if title:
            topics.append((title, str(episode_path.relative_to(ROOT_DIR))))
    return topics


def check_duplicate_topic(topic: str, *, allow_similar: bool) -> dict:
    normalized = normalize_topic(topic)
    if len(normalized) < 5:
        raise ValueError(
            "주제가 너무 짧거나 모호합니다. 질문 형태의 구체적인 주제를 입력하세요."
        )

    nearest: dict | None = None
    for previous_topic, source in known_topics():
        previous_normalized = normalize_topic(previous_topic)
        if not previous_normalized:
            continue
        ratio = SequenceMatcher(None, normalized, previous_normalized).ratio()
        containment = 0.0
        if normalized in previous_normalized or previous_normalized in normalized:
            containment = min(len(normalized), len(previous_normalized)) / max(
                len(normalized), len(previous_normalized)
            )
        similarity = max(ratio, containment)
        if nearest is None or similarity > nearest["similarity"]:
            nearest = {
                "topic": previous_topic,
                "source": source,
                "similarity": similarity,
            }

    threshold = 0.72
    if nearest and nearest["similarity"] >= threshold and not allow_similar:
        raise ValueError(
            "이미 제작했거나 매우 유사한 주제입니다: "
            f"'{nearest['topic']}' ({nearest['similarity']:.0%})"
        )
    return {
        "status": "passed",
        "threshold": threshold,
        "nearestMatch": nearest,
    }


def build_candidate(topic: str, category: str, angle: str) -> dict:
    normalized_topic = topic.strip()
    if not normalized_topic:
        raise ValueError("주제가 비어 있습니다.")
    return {
        "category": category,
        "mode": "direct-topic-local",
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
                    f"{normalized_topic} fact check",
                    f"{normalized_topic} image archive",
                ],
                "production_ready": True,
                "readiness_score": 100,
                "readiness_checks": ["사용자 직접 선택 주제"],
            }
        ],
    }


def run_topic_preflight(candidate_payload: dict) -> dict:
    print("\n" + "=" * 62)
    print("[단계] 출처와 미디어 실제 사전검증")
    print("=" * 62)
    result = CandidatePreflightService().filter_payload(candidate_payload, limit=1)
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        rejected = (result.get("preflight") or {}).get("rejected") or []
        reason = rejected[0].get("reason") if rejected else "검증 가능한 자료나 이미지 부족"
        raise TopicPreflightError(f"주제 사전검증 실패: {reason}")

    candidate = candidates[0]
    source_count = int((candidate.get("source_preflight") or {}).get("documentCount", 0))
    domain_count = int((candidate.get("source_preflight") or {}).get("domainCount", 0))
    media_count = int((candidate.get("preflight_media") or {}).get("candidateCount", 0))
    query_count = int(
        (candidate.get("preflight_media") or {}).get("successfulQueryCount", 0)
    )
    print(f"검증 자료: {source_count}건 / 독립 출처: {domain_count}곳")
    print(f"다운로드 가능한 이미지: {media_count}개 / 검색어: {query_count}개")
    print("사전검증 통과")
    return result


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    args = parse_args()

    try:
        duplicate_result = check_duplicate_topic(
            args.topic,
            allow_similar=args.allow_similar_topic,
        )
        verified_payload = run_topic_preflight(
            build_candidate(args.topic, args.category, args.angle)
        )
        episode_id = resolve_episode_id(args.episode)
        episode_dir = ROOT_DIR / "projects" / "episodes" / episode_id
        if episode_dir.exists():
            raise RuntimeError(f"이미 존재하는 에피소드입니다: {episode_id}")
        episode_dir.mkdir(parents=True)

        preflight_path = episode_dir / "preflight.json"
        evidence_path = episode_dir / "evidence.json"
        episode_path = episode_dir / "episode.json"
        metadata_path = episode_dir / "metadata.json"
        verified_payload["duplicateCheck"] = duplicate_result
        write_json(preflight_path, verified_payload)

        run_step(
            "토큰 없는 로컬 대본과 메타데이터 생성",
            [
                sys.executable,
                "projects/production/build_local_episode.py",
                "--preflight",
                str(preflight_path),
                "--episode-id",
                episode_id,
                "--category",
                args.category,
                "--topic",
                args.topic,
                "--angle",
                args.angle,
                "--episode-output",
                str(episode_path),
                "--metadata-output",
                str(metadata_path),
                "--evidence-output",
                str(evidence_path),
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

    except (
        OSError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
        TopicPreflightError,
    ) as exc:
        print(f"\n[제작 실패] {exc}")
        return 1

    print("\n" + "=" * 62)
    print("영상 제작 완료" if not args.prepare_only else "영상 패키지 준비 완료")
    print("생성 방식: local_public_sources (GitHub 토큰 불필요)")
    print(f"에피소드: {episode_id}")
    print(f"주제: {args.topic.strip()}")
    print(f"Preflight: {preflight_path}")
    print(f"Episode: {episode_path}")
    print(f"Metadata: {metadata_path}")
    if not args.prepare_only:
        print(f"MP4: {ROOT_DIR / 'projects' / 'output' / f'{episode_id}.mp4'}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
