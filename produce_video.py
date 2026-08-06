from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
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


AUTO_TOPICS = [
    {
        "topic": "오징어의 피는 왜 파란색일까?",
        "category": "science",
        "angle": "구리를 포함한 헤모시아닌과 해양 환경의 관계",
        "queries": [
            "squid blue blood hemocyanin",
            "cephalopod circulatory system",
            "squid anatomy scientific illustration",
            "squid underwater close up",
            "hemocyanin oxygen transport diagram",
        ],
        "interest": 94,
    },
    {
        "topic": "상어는 왜 계속 헤엄쳐야 할까?",
        "category": "science",
        "angle": "상어 종류에 따라 달라지는 호흡 방식",
        "queries": [
            "shark swimming underwater",
            "shark ram ventilation",
            "shark gill anatomy diagram",
            "shark resting seabed",
            "shark respiration scientific illustration",
        ],
        "interest": 92,
    },
    {
        "topic": "해마는 왜 수컷이 새끼를 낳을까?",
        "category": "science",
        "angle": "수컷의 육아주머니와 번식 과정",
        "queries": [
            "male seahorse giving birth",
            "seahorse brood pouch anatomy",
            "seahorse reproduction scientific illustration",
            "seahorse underwater close up",
            "pregnant male seahorse",
        ],
        "interest": 93,
    },
    {
        "topic": "홍학은 왜 한쪽 다리로 서 있을까?",
        "category": "science",
        "angle": "체온 손실과 안정적인 관절 구조",
        "queries": [
            "flamingo standing one leg",
            "flamingo leg anatomy",
            "flamingo flock wetland",
            "flamingo thermoregulation study",
            "flamingo close up",
        ],
        "interest": 89,
    },
    {
        "topic": "딱따구리는 왜 머리가 아프지 않을까?",
        "category": "science",
        "angle": "충격을 분산하는 머리와 목의 구조",
        "queries": [
            "woodpecker pecking tree slow motion",
            "woodpecker skull anatomy",
            "woodpecker tongue anatomy illustration",
            "woodpecker close up",
            "woodpecker impact biomechanics",
        ],
        "interest": 91,
    },
    {
        "topic": "북극곰의 털은 정말 흰색일까?",
        "category": "science",
        "angle": "투명한 털과 검은 피부가 만드는 색",
        "queries": [
            "polar bear fur close up",
            "polar bear black skin",
            "polar bear transparent hair microscope",
            "polar bear arctic",
            "polar bear fur scientific illustration",
        ],
        "interest": 90,
    },
    {
        "topic": "금붕어의 기억력은 정말 3초일까?",
        "category": "science",
        "angle": "실험으로 확인된 학습과 장기 기억",
        "queries": [
            "goldfish swimming aquarium",
            "goldfish memory experiment",
            "goldfish learning research",
            "goldfish close up",
            "fish cognition scientific illustration",
        ],
        "interest": 88,
    },
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "주제 자동선정 또는 직접 입력으로 자료·미디어 검증, 대본 생성, "
            "TTS, 자막, Remotion 렌더까지 실행합니다."
        )
    )
    parser.add_argument("topic", nargs="?", help="직접 제작할 영상 주제")
    parser.add_argument(
        "--auto",
        action="store_true",
        help="후보를 자동 검사하고 제작 성공 가능성이 가장 높은 주제를 선택합니다.",
    )
    parser.add_argument(
        "--category",
        choices=SUPPORTED_CATEGORIES,
        default="science",
        help="직접 입력 주제의 카테고리 (기본값: science)",
    )
    parser.add_argument("--episode", default="auto")
    parser.add_argument("--angle", default="")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--skip-typecheck", action="store_true")
    parser.add_argument("--allow-similar-topic", action="store_true")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not args.auto and not args.topic:
        parser.error("주제를 입력하거나 --auto를 사용하세요.")
    return args


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
        raise ValueError("에피소드 형식이 올바르지 않습니다. 예: ep033 또는 auto")
    from projects.production.select_topic import next_episode_id
    return next_episode_id(ROOT_DIR)


def normalize_topic(value: str) -> str:
    normalized = re.sub(r"[\s\W_]+", "", value.strip().lower(), flags=re.UNICODE)
    for old, new in {
        "세개": "3개",
        "두개": "2개",
        "한개": "1개",
        "진짜이유": "이유",
        "이유는무엇일까": "이유",
        "왜그럴까": "왜",
    }.items():
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


def nearest_topic(topic: str) -> dict | None:
    normalized = normalize_topic(topic)
    nearest: dict | None = None
    for previous_topic, source in known_topics():
        previous = normalize_topic(previous_topic)
        if not previous:
            continue
        ratio = SequenceMatcher(None, normalized, previous).ratio()
        containment = 0.0
        if normalized in previous or previous in normalized:
            containment = min(len(normalized), len(previous)) / max(len(normalized), len(previous))
        similarity = max(ratio, containment)
        if nearest is None or similarity > nearest["similarity"]:
            nearest = {"topic": previous_topic, "source": source, "similarity": similarity}
    return nearest


def check_duplicate_topic(topic: str, *, allow_similar: bool) -> dict:
    normalized = normalize_topic(topic)
    if len(normalized) < 5:
        raise ValueError("주제가 너무 짧거나 모호합니다.")
    nearest = nearest_topic(topic)
    threshold = 0.72
    if nearest and nearest["similarity"] >= threshold and not allow_similar:
        raise ValueError(
            f"이미 제작했거나 매우 유사한 주제입니다: '{nearest['topic']}' "
            f"({nearest['similarity']:.0%})"
        )
    return {"status": "passed", "threshold": threshold, "nearestMatch": nearest}


def expanded_queries(topic: str, category: str) -> list[str]:
    normalized = normalize_topic(topic)
    for item in AUTO_TOPICS:
        if normalize_topic(item["topic"]) == normalized:
            return list(item["queries"])
    subject = re.sub(r"[?？]", "", topic).strip()
    category_terms = {
        "science": ["scientific illustration", "anatomy", "research", "close up"],
        "mystery": ["artifact", "museum archive", "historical illustration", "documentary"],
        "history": ["museum", "historical reconstruction", "archive", "artifact"],
        "space": ["NASA", "ESA", "space illustration", "telescope image"],
    }[category]
    return [subject, *[f"{subject} {term}" for term in category_terms]]


def build_candidate(topic: str, category: str, angle: str, queries: list[str] | None = None) -> dict:
    return {
        "category": category,
        "mode": "auto-local" if queries else "direct-topic-local",
        "candidates": [{
            "rank": 1,
            "category": category,
            "topic": topic.strip(),
            "angle": angle.strip(),
            "score": 100,
            "reasons": ["사용자 직접 선택" if not queries else "자동 후보 선정"],
            "search_queries": queries or expanded_queries(topic, category),
            "production_ready": True,
            "readiness_score": 100,
            "readiness_checks": ["구체적 주제와 영문 미디어 검색어 확보"],
        }],
    }


def preflight_service() -> CandidatePreflightService:
    # 쇼츠에서는 같은 원본을 확대·크롭·좌우 반전해 장면별로 재활용할 수 있습니다.
    # 따라서 고유 이미지 2개와 성공 검색어 1개를 최소 제작 기준으로 둡니다.
    return CandidatePreflightService(
        minimum_media_candidates=2,
        minimum_media_queries=1,
        maximum_candidates_checked=1,
    )


def run_topic_preflight(candidate_payload: dict) -> dict:
    print("\n" + "=" * 62)
    print("[단계] 출처와 미디어 실제 사전검증")
    print("=" * 62)
    result = preflight_service().filter_payload(candidate_payload, limit=1)
    candidates = result.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        rejected = (result.get("preflight") or {}).get("rejected") or []
        reason = rejected[0].get("reason") if rejected else "검증 가능한 자료나 이미지 부족"
        raise TopicPreflightError(f"주제 사전검증 실패: {reason}")
    candidate = candidates[0]
    source = candidate.get("source_preflight") or {}
    media = candidate.get("preflight_media") or {}
    print(f"검증 자료: {source.get('documentCount', 0)}건 / 독립 출처: {source.get('domainCount', 0)}곳")
    print(f"다운로드 가능한 고유 이미지: {media.get('candidateCount', 0)}개")
    print("부족한 장면은 확대·크롭·반전 방식으로 원본을 재활용합니다.")
    return result


def select_auto_topic() -> tuple[str, str, str, dict]:
    print("\n" + "=" * 62)
    print("[단계] 주제 자동선정")
    print("=" * 62)
    ordered = sorted(AUTO_TOPICS, key=lambda item: item["interest"], reverse=True)
    failures: list[str] = []
    for item in ordered:
        nearest = nearest_topic(item["topic"])
        if nearest and nearest["similarity"] >= 0.72:
            print(f"[제외] {item['topic']} - 기존 주제와 유사")
            continue
        print(f"[검사] {item['topic']} (흥미도 {item['interest']})")
        try:
            result = run_topic_preflight(
                build_candidate(item["topic"], item["category"], item["angle"], item["queries"])
            )
        except TopicPreflightError as exc:
            failures.append(f"{item['topic']}: {exc}")
            print(f"[제외] {exc}")
            continue
        print(f"[자동 선택] {item['topic']}")
        return item["topic"], item["category"], item["angle"], result
    detail = "\n".join(failures[-3:])
    raise TopicPreflightError(f"자동 후보가 모두 사전검증에 실패했습니다.\n{detail}")


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON 최상위 값은 객체여야 합니다: {path}")
    return payload


def write_status(episode_dir: Path, *, status: str, detail: str = "") -> None:
    write_json(episode_dir / "production-status.json", {
        "status": status,
        "detail": detail,
        "updatedAt": datetime.now(timezone.utc).isoformat(),
    })


def remember_published_topic(topic: str) -> None:
    path = ROOT_DIR / "config" / "published_topics.json"
    payload = {"topics": []}
    if path.exists():
        try:
            payload = read_json(path)
        except (OSError, json.JSONDecodeError, ValueError):
            pass
    topics = payload.get("topics") if isinstance(payload.get("topics"), list) else []
    if normalize_topic(topic) not in {normalize_topic(str(value)) for value in topics}:
        topics.append(topic.strip())
    payload["topics"] = topics
    write_json(path, payload)


def validate_mp4(path: Path) -> None:
    if not path.exists() or path.stat().st_size < 10_000:
        raise RuntimeError(f"정상 MP4가 생성되지 않았습니다: {path}")


def main() -> int:
    args = parse_args()
    episode_id = ""
    episode_dir: Path | None = None
    topic = args.topic or ""
    category = args.category
    angle = args.angle

    try:
        episode_id = resolve_episode_id(args.episode)
        episode_dir = ROOT_DIR / "projects" / "episodes" / episode_id
        preflight_path = episode_dir / "preflight.json"
        evidence_path = episode_dir / "evidence.json"
        episode_path = episode_dir / "episode.json"
        metadata_path = episode_dir / "metadata.json"
        mp4_path = ROOT_DIR / "projects" / "output" / f"{episode_id}.mp4"

        if episode_dir.exists() and not args.resume:
            raise RuntimeError(f"이미 존재하는 에피소드입니다: {episode_id}. --resume을 사용하세요.")
        episode_dir.mkdir(parents=True, exist_ok=True)
        write_status(episode_dir, status="started")

        if args.resume and preflight_path.exists():
            verified_payload = read_json(preflight_path)
            candidate = (verified_payload.get("candidates") or [{}])[0]
            topic = str(candidate.get("topic") or topic)
            category = str(candidate.get("category") or category)
            angle = str(candidate.get("angle") or angle)
            print(f"[재사용] {preflight_path}")
        elif args.auto:
            topic, category, angle, verified_payload = select_auto_topic()
            verified_payload["duplicateCheck"] = {"status": "passed", "mode": "auto"}
            write_json(preflight_path, verified_payload)
        else:
            duplicate_result = check_duplicate_topic(topic, allow_similar=args.allow_similar_topic)
            verified_payload = run_topic_preflight(build_candidate(topic, category, angle))
            verified_payload["duplicateCheck"] = duplicate_result
            write_json(preflight_path, verified_payload)
        write_status(episode_dir, status="preflight_ready", detail=topic)

        package_ready = episode_path.exists() and metadata_path.exists() and evidence_path.exists()
        if args.resume and package_ready:
            print("[재사용] episode.json, metadata.json, evidence.json")
        else:
            run_step("토큰 없는 로컬 대본과 메타데이터 생성", [
                sys.executable,
                "projects/production/build_local_episode.py",
                "--preflight", str(preflight_path),
                "--episode-id", episode_id,
                "--category", category,
                "--topic", topic,
                "--angle", angle,
                "--episode-output", str(episode_path),
                "--metadata-output", str(metadata_path),
                "--evidence-output", str(evidence_path),
            ])
        write_status(episode_dir, status="package_ready")

        if not args.prepare_only:
            if args.resume and mp4_path.exists():
                validate_mp4(mp4_path)
                print(f"[재사용] {mp4_path}")
            else:
                command = [sys.executable, "factory_runner.py", "--episode", episode_id, "--rebuild-timeline"]
                if args.skip_typecheck:
                    command.append("--skip-typecheck")
                run_step("미디어 수집과 MP4 렌더", command)
                validate_mp4(mp4_path)
            remember_published_topic(topic)
            write_status(episode_dir, status="completed", detail=str(mp4_path))
        else:
            write_status(episode_dir, status="prepared")

    except (OSError, ValueError, RuntimeError, json.JSONDecodeError, TopicPreflightError) as exc:
        if episode_dir is not None and episode_dir.exists():
            try:
                write_status(episode_dir, status="failed", detail=str(exc))
            except OSError:
                pass
        print(f"\n[제작 실패] {exc}")
        if episode_id:
            auto_flag = " --auto" if args.auto else f' "{topic}"'
            print(f"재실행: py produce_video.py{auto_flag} --episode {episode_id} --resume")
        return 1

    print("\n" + "=" * 62)
    print("영상 제작 완료" if not args.prepare_only else "영상 패키지 준비 완료")
    print(f"에피소드: {episode_id}")
    print(f"자동 선정 주제: {topic}" if args.auto else f"주제: {topic}")
    print(f"Metadata: {metadata_path}")
    if not args.prepare_only:
        print(f"MP4: {mp4_path}")
    print("=" * 62)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
