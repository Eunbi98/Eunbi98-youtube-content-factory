from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Protocol
from urllib.parse import urlencode

from .topic_catalog import CATEGORY_QUERIES
from .topic_models import TopicSourceItem


class TopicSource(Protocol):
    def fetch(
        self,
        *,
        category: str,
        limit: int,
    ) -> list[TopicSourceItem]: ...


class GoogleNewsTopicSource:
    """API 키 없이 최근 한국어 뉴스 제목을 수집합니다."""

    BASE_URL = "https://news.google.com/rss/search"

    def __init__(self, *, timeout_seconds: float = 12.0) -> None:
        self._timeout_seconds = timeout_seconds

    def fetch(
        self,
        *,
        category: str,
        limit: int,
    ) -> list[TopicSourceItem]:
        try:
            import feedparser
            import requests
        except ImportError as exc:
            raise RuntimeError(
                "실시간 뉴스 수집 의존성이 없습니다. "
                "requirements.txt를 설치해 주세요."
            ) from exc

        queries = CATEGORY_QUERIES.get(category)
        if queries is None:
            raise ValueError(f"지원하지 않는 카테고리입니다: {category}")

        collected: list[TopicSourceItem] = []
        seen_urls: set[str] = set()

        for query in queries:
            params = urlencode(
                {
                    "q": f"{query} when:14d",
                    "hl": "ko",
                    "gl": "KR",
                    "ceid": "KR:ko",
                }
            )
            response = requests.get(
                f"{self.BASE_URL}?{params}",
                headers={
                    "User-Agent": (
                        "YouTubeAIFactory/1.0 "
                        "(+https://github.com/Eunbi98)"
                    )
                },
                timeout=self._timeout_seconds,
            )
            response.raise_for_status()

            feed = feedparser.parse(response.content)
            for entry in feed.entries:
                url = str(entry.get("link") or "").strip()
                title = str(entry.get("title") or "").strip()
                if not title or not url or url in seen_urls:
                    continue

                seen_urls.add(url)
                source_data = entry.get("source") or {}
                source_name = str(
                    source_data.get("title") or "Google News"
                ).strip()
                published_at = self._published_at(entry)
                collected.append(
                    TopicSourceItem(
                        title=title,
                        url=url,
                        source=source_name,
                        published_at=published_at,
                    )
                )

                if len(collected) >= limit:
                    return collected

        return collected

    @staticmethod
    def _published_at(entry: Any) -> str | None:
        parsed = getattr(entry, "published_parsed", None)
        if parsed is None:
            return None

        try:
            return datetime(
                *parsed[:6],
                tzinfo=timezone.utc,
            ).isoformat()
        except (TypeError, ValueError):
            return None
