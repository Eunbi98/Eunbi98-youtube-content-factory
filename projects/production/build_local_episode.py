from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[2]
TEMPLATE_PATH = ROOT_DIR / "config" / "local_topic_templates.json"


class LocalEpisodeError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LocalEpisodeError(f"최상위 값은 객체여야 합니다: {path}")
    return payload


def _normalize(value: str) -> str:
    return re.sub(r"[\s\W_]+", "", value.strip().lower(), flags=re.UNICODE)


def _clean_sentence(value: str, *, limit: int = 125) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"https?://\S+", "", text).strip()
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
    if text[-1] not in ".?!다요죠":
        text += "."
    return text


def _load_template(topic: str) -> dict[str, Any] | None:
    if not TEMPLATE_PATH.exists():
        return None
    payload = _load(TEMPLATE_PATH)
    normalized_topic = _normalize(topic)
    for key, value in payload.items():
        if _normalize(str(key)) == normalized_topic and isinstance(value, dict):
            return value
    return None


def _template_package(
    *,
    template: dict[str, Any],
    preflight: dict[str, Any],
    episode_id: str,
    category: str,
    topic: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    raw_scenes = template.get("scenes")
    if not isinstance(raw_scenes, list) or len(raw_scenes) != 6:
        raise LocalEpisodeError("검증된 주제 템플릿은 정확히 6개 Scene이어야 합니다.")

    candidates = preflight.get("candidates")
    candidate = candidates[0] if isinstance(candidates, list) and candidates else {}
    sources = candidate.get("preflight_sources") if isinstance(candidate, dict) else []
    if not isinstance(sources, list):
        sources = []
    evidence_ids = [f"source_{index + 1}" for index in range(len(sources))]

    scenes: list[dict[str, Any]] = []
    for raw_scene in raw_scenes:
        if not isinstance(raw_scene, dict):
            raise LocalEpisodeError("주제 템플릿 Scene 형식이 올바르지 않습니다.")
        narration = _clean_sentence(str(raw_scene.get("narration") or ""))
        keywords = [
            str(value).strip()
            for value in raw_scene.get("keywords", [])
            if str(value).strip()
        ]
        if not narration or not keywords:
            raise LocalEpisodeError("주제 템플릿의 narration 또는 keywords가 비어 있습니다.")
        scenes.append(
            {
                "type": str(raw_scene.get("type") or "fact"),
                "title": str(raw_scene.get("title") or topic.rstrip("?")),
                "narration": narration,
                "keywords": keywords,
                "evidenceIds": evidence_ids,
            }
        )

    all_narration = " ".join(scene["narration"] for scene in scenes)
    required_terms = ["헤모시아닌", "구리", "산소", "파란"] if "오징어" in topic and "파란" in topic else []
    missing_terms = [term for term in required_terms if term not in all_narration]
    if missing_terms:
        raise LocalEpisodeError(
            "제목의 핵심 질문에 답하는 필수 개념이 대본에 없습니다: "
            + ", ".join(missing_terms)
        )

    episode = {
        "version": "1.0",
        "episodeId": episode_id,
        "channel": category,
        "title": str(template.get("title") or topic.rstrip("?")),
        "voice": "ko-KR-SunHiNeural",
        "theme": {
            "backgroundColor": "#000000",
            "titleColor": "#7CFFB2",
            "captionColor": "#FFFFFF",
            "accentColor": "#7CFFB2",
        },
        "scenes": scenes,
    }

    source_urls = [
        str(source.get("source_url") or "")
        for source in sources
        if isinstance(source, dict) and source.get("source_url")
    ]
    metadata = {
        "episodeId": episode_id,
        "title": str(template.get("title") or topic.rstrip("?")),
        "description": str(template.get("description") or ""),
        "pinnedComment": str(template.get("pinnedComment") or ""),
        "tags": [str(tag) for tag in template.get("tags", []) if str(tag).strip()],
        "sources": source_urls[:5],
    }
    evidence = {
        "topic": topic,
        "status": "verified",
        "provider": "local_verified_template",
        "summary": " ".join(scene["narration"] for scene in scenes[1:5]),
        "uncertainties": [],
        "items": [
            {
                "id": f"source_{index + 1}",
                "title": str(source.get("title") or ""),
                "claim": _clean_sentence(str(source.get("text") or ""), limit=400),
                "source_name": str(source.get("source_name") or ""),
                "source_url": str(source.get("source_url") or ""),
                "source_tier": str(source.get("source_tier") or "unknown"),
            }
            for index, source in enumerate(sources)
            if isinstance(source, dict)
        ],
    }
    return episode, metadata, evidence


def build_package(
    *,
    preflight: dict[str, Any],
    episode_id: str,
    category: str,
    topic: str,
    angle: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    template = _load_template(topic)
    if template is None:
        raise LocalEpisodeError(
            "토큰 없는 모드에서는 검증된 주제 템플릿이 필요합니다. "
            "자동 후보에 등록된 주제를 사용하거나 템플릿을 먼저 추가하세요."
        )
    return _template_package(
        template=template,
        preflight=preflight,
        episode_id=episode_id,
        category=category,
        topic=topic,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="검증된 로컬 템플릿으로 Episode를 생성합니다.")
    parser.add_argument("--preflight", type=Path, required=True)
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--topic", required=True)
    parser.add_argument("--angle", default="")
    parser.add_argument("--episode-output", type=Path, required=True)
    parser.add_argument("--metadata-output", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    args = parser.parse_args()

    try:
        episode, metadata, evidence = build_package(
            preflight=_load(args.preflight),
            episode_id=args.episode_id,
            category=args.category,
            topic=args.topic,
            angle=args.angle,
        )
        for path, payload in (
            (args.episode_output, episode),
            (args.metadata_output, metadata),
            (args.evidence_output, evidence),
        ):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
    except (OSError, json.JSONDecodeError, LocalEpisodeError) as exc:
        print(f"[실패] {exc}")
        return 2

    print("검증된 로컬 Episode 생성 완료")
    print(f"Episode: {args.episode_output}")
    print(f"Metadata: {args.metadata_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
