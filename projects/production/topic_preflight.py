from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Iterable


class TopicPreflightError(ValueError):
    """주제 사전검사 실패."""


@dataclass(frozen=True)
class TopicMatch:
    topic: str
    source: str
    similarity: float


@dataclass(frozen=True)
class TopicPreflightResult:
    topic: str
    normalized_topic: str
    passed: bool
    duplicate_threshold: float
    nearest_match: TopicMatch | None
    research_queries: list[str]
    media_queries: list[str]
    available_media_providers: list[str]
    warnings: list[str]

    def to_dict(self) -> dict:
        payload = asdict(self)
        return payload


class TopicPreflightService:
    def __init__(
        self,
        *,
        root_dir: Path,
        duplicate_threshold: float = 0.72,
    ) -> None:
        self.root_dir = root_dir
        self.duplicate_threshold = duplicate_threshold

    def inspect(self, *, topic: str, category: str, render: bool) -> TopicPreflightResult:
        normalized = self.normalize(topic)
        if len(normalized) < 5:
            raise TopicPreflightError(
                "주제가 너무 짧거나 모호합니다. 질문 형태의 구체적인 주제를 입력하세요."
            )

        known_topics = list(self._known_topics())
        nearest = self._nearest_match(normalized, known_topics)
        if nearest and nearest.similarity >= self.duplicate_threshold:
            raise TopicPreflightError(
                "이미 제작했거나 매우 유사한 주제입니다: "
                f"'{nearest.topic}' ({nearest.similarity:.0%}, {nearest.source})"
            )

        providers = self._available_media_providers()
        warnings: list[str] = []
        if render and not providers:
            raise TopicPreflightError(
                "렌더에 사용할 미디어 API 키가 없습니다. "
                "PIXABAY_API_KEY 또는 PEXELS_API_KEY를 설정하세요."
            )
        if not providers:
            warnings.append("미디어 API 키가 없어 패키지 준비까지만 권장됩니다.")

        return TopicPreflightResult(
            topic=topic.strip(),
            normalized_topic=normalized,
            passed=True,
            duplicate_threshold=self.duplicate_threshold,
            nearest_match=nearest,
            research_queries=self._research_queries(topic.strip(), category),
            media_queries=self._media_queries(topic.strip(), category),
            available_media_providers=providers,
            warnings=warnings,
        )

    @staticmethod
    def normalize(value: str) -> str:
        lowered = value.strip().lower()
        lowered = re.sub(r"[\s\W_]+", "", lowered, flags=re.UNICODE)
        replacements = {
            "세개": "3개",
            "두개": "2개",
            "한개": "1개",
            "진짜이유": "이유",
            "이유는무엇일까": "이유",
            "왜그럴까": "왜",
        }
        for old, new in replacements.items():
            lowered = lowered.replace(old, new)
        return lowered

    def _known_topics(self) -> Iterable[tuple[str, str]]:
        published_path = self.root_dir / "config" / "published_topics.json"
        if published_path.exists():
            try:
                payload = json.loads(published_path.read_text(encoding="utf-8"))
                for topic in payload.get("topics", []):
                    text = str(topic).strip()
                    if text:
                        yield text, "config/published_topics.json"
            except (OSError, json.JSONDecodeError, AttributeError):
                pass

        episodes_dir = self.root_dir / "projects" / "episodes"
        for episode_path in episodes_dir.glob("ep*/episode.json"):
            try:
                payload = json.loads(episode_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            title = str(payload.get("title") or "").strip()
            if title:
                yield title, str(episode_path.relative_to(self.root_dir))
            scenes = payload.get("scenes")
            if isinstance(scenes, list) and scenes:
                hook_title = str(scenes[0].get("title") or "").strip()
                if hook_title:
                    yield hook_title, str(episode_path.relative_to(self.root_dir))

    def _nearest_match(
        self,
        normalized_topic: str,
        known_topics: Iterable[tuple[str, str]],
    ) -> TopicMatch | None:
        nearest: TopicMatch | None = None
        for topic, source in known_topics:
            candidate = self.normalize(topic)
            if not candidate:
                continue
            ratio = SequenceMatcher(None, normalized_topic, candidate).ratio()
            containment = min(len(normalized_topic), len(candidate)) / max(
                len(normalized_topic), len(candidate)
            ) if normalized_topic in candidate or candidate in normalized_topic else 0.0
            similarity = max(ratio, containment)
            if nearest is None or similarity > nearest.similarity:
                nearest = TopicMatch(topic=topic, source=source, similarity=similarity)
        return nearest

    @staticmethod
    def _available_media_providers() -> list[str]:
        providers = []
        if os.getenv("PIXABAY_API_KEY"):
            providers.append("pixabay")
        if os.getenv("PEXELS_API_KEY"):
            providers.append("pexels")
        return providers

    @staticmethod
    def _research_queries(topic: str, category: str) -> list[str]:
        suffix = {
            "science": "scientific study official source",
            "mystery": "historical record fact check",
            "history": "primary source museum archive",
            "space": "NASA ESA official observation",
        }.get(category, "official source research")
        return [
            topic,
            f"{topic} {suffix}",
            f"{topic} evidence limitations",
        ]

    @staticmethod
    def _media_queries(topic: str, category: str) -> list[str]:
        visual_hint = {
            "science": "scientific illustration animation",
            "mystery": "artifact archive documentary",
            "history": "museum archive historical reconstruction",
            "space": "NASA image animation",
        }.get(category, "documentary image")
        return [
            f"{topic} {visual_hint}",
            f"{topic} close up",
            f"{topic} educational animation",
        ]
