from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any


class LocalEpisodeError(ValueError):
    pass


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise LocalEpisodeError(f"최상위 값은 객체여야 합니다: {path}")
    return payload


def _clean_sentence(value: str, *, limit: int = 105) -> str:
    text = re.sub(r"\s+", " ", value).strip()
    text = re.sub(r"https?://\S+", "", text).strip()
    if not text:
        return ""
    if len(text) > limit:
        text = text[:limit].rsplit(" ", 1)[0].rstrip(" ,.;:")
    if text[-1] not in ".?!다요죠":
        text += "."
    return text


def _sentences(text: str) -> list[str]:
    values = re.split(r"(?<=[.!?。])\s+|\n+", text)
    result: list[str] = []
    for value in values:
        cleaned = _clean_sentence(value)
        if len(cleaned) >= 18 and cleaned not in result:
            result.append(cleaned)
    return result


def _keywords(topic: str, source_title: str = "") -> list[str]:
    base = re.sub(r"[?!.]", "", topic).strip()
    values = [
        f"{base} documentary",
        f"{base} scientific illustration",
        source_title,
    ]
    return [value for value in dict.fromkeys(values) if value]


def build_package(
    *,
    preflight: dict[str, Any],
    episode_id: str,
    category: str,
    topic: str,
    angle: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    candidates = preflight.get("candidates")
    if not isinstance(candidates, list) or not candidates:
        raise LocalEpisodeError("사전검증을 통과한 후보가 없습니다.")
    candidate = candidates[0]
    sources = candidate.get("preflight_sources")
    if not isinstance(sources, list) or len(sources) < 2:
        raise LocalEpisodeError("로컬 대본 생성에 필요한 공개 자료가 부족합니다.")

    extracted: list[tuple[str, str, str]] = []
    for source in sources:
        if not isinstance(source, dict):
            continue
        title = str(source.get("title") or "").strip()
        url = str(source.get("source_url") or "").strip()
        for sentence in _sentences(str(source.get("text") or "")):
            extracted.append((sentence, title, url))
            if len(extracted) >= 8:
                break
        if len(extracted) >= 8:
            break

    if len(extracted) < 3:
        raise LocalEpisodeError("자료 본문에서 충분한 설명 문장을 추출하지 못했습니다.")

    facts = extracted[:4]
    hook = f"{topic} 그 이유를 확인된 자료를 바탕으로 살펴보겠습니다."
    ending = f"{topic} 여러분은 이 사실을 알고 계셨나요?"
    scene_types = ["hook", "answer", "story", "fact", "fact", "ending"]
    scene_titles = [
        topic.rstrip("?"),
        "첫 번째 핵심 사실",
        "자료가 보여주는 이유",
        "추가로 확인된 사실",
        "아직 남은 해석",
        "여러분의 생각은?",
    ]
    narrations = [
        hook,
        facts[0][0],
        facts[1][0],
        facts[2][0],
        facts[3][0] if len(facts) > 3 else "자료에 따라 세부 설명에는 차이가 있어 단정적으로 해석하지 않는 것이 중요합니다.",
        ending,
    ]

    evidence_ids = [f"source_{index + 1}" for index in range(len(sources))]
    scenes = []
    for index, narration in enumerate(narrations):
        source_title = facts[min(max(index - 1, 0), len(facts) - 1)][1] if 1 <= index <= 4 else ""
        scenes.append(
            {
                "type": scene_types[index],
                "title": scene_titles[index],
                "narration": _clean_sentence(narration, limit=125),
                "keywords": _keywords(topic, source_title),
                "evidenceIds": evidence_ids,
            }
        )

    episode = {
        "version": "1.0",
        "episodeId": episode_id,
        "channel": category,
        "title": topic.rstrip("?"),
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
    description_lines = [
        topic,
        "",
        *[fact[0] for fact in facts[:3]],
        "",
        ending,
    ]
    tags = [
        re.sub(r"\s+", "", topic.replace("?", ""))[:20],
        category,
        "과학상식" if category == "science" else "흥미로운이야기",
        "상식",
        "쇼츠",
        "shorts",
    ]
    metadata = {
        "episodeId": episode_id,
        "title": topic.rstrip("?"),
        "description": "\n".join(description_lines),
        "pinnedComment": ending + " 댓글로 생각을 남겨주세요.",
        "tags": list(dict.fromkeys(tag for tag in tags if tag)),
        "sources": source_urls[:5],
    }
    evidence = {
        "topic": topic,
        "status": "verified",
        "provider": "local_public_sources",
        "summary": " ".join(fact[0] for fact in facts[:3]),
        "uncertainties": [
            "로컬 규칙 기반 생성 결과이므로 최종 업로드 전에 문장과 사실관계를 검토하세요."
        ],
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


def main() -> int:
    parser = argparse.ArgumentParser(description="토큰 없이 공개 자료로 Episode를 생성합니다.")
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

    print("토큰 없는 로컬 Episode 생성 완료")
    print(f"Episode: {args.episode_output}")
    print(f"Metadata: {args.metadata_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
