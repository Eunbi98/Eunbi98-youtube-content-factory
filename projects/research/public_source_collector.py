from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Callable
from urllib.parse import quote, urlparse


class PublicSourceError(RuntimeError):
    """무료 공개 자료 수집 오류."""


@dataclass(frozen=True)
class SourceDocument:
    id: str
    title: str
    source_name: str
    source_url: str
    source_tier: str
    published_at: str
    text: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


Get = Callable[..., Any]


class PublicSourceCollector:
    """API 키가 필요 없는 공개 자료에서 검증용 문서를 모읍니다."""

    WIKI_APIS = (
        ("https://ko.wikipedia.org/w/api.php", "한국어 위키백과"),
        ("https://en.wikipedia.org/w/api.php", "Wikipedia"),
    )
    OPENALEX_API = "https://api.openalex.org/works"

    def __init__(
        self,
        *,
        get: Get | None = None,
        timeout_seconds: float = 20.0,
    ) -> None:
        self._get = get
        self._timeout_seconds = timeout_seconds

    def collect(
        self,
        job_payload: dict[str, Any],
        *,
        search_queries: list[str] | None = None,
    ) -> list[dict[str, str]]:
        selected = job_payload.get("selectedTopic")
        if not isinstance(selected, dict):
            raise PublicSourceError("Production Job의 selectedTopic이 없습니다.")
        topic = str(selected.get("topic") or "").strip()
        if not topic:
            raise PublicSourceError("선택 주제가 비어 있습니다.")

        raw_documents: list[dict[str, str]] = []
        for source in selected.get("sources", []):
            if not isinstance(source, dict):
                continue
            document = self._fetch_web_document(
                url=str(source.get("url") or ""),
                fallback_title=str(source.get("title") or topic),
                fallback_source=str(source.get("source") or "News source"),
                published_at=str(source.get("published_at") or ""),
                source_tier="news",
            )
            if document:
                raw_documents.append(document)

        normalized_queries = [
            str(query).strip()
            for query in (search_queries or [])
            if str(query).strip()
        ]
        wiki_requests = [
            (self.WIKI_APIS[0][0], self.WIKI_APIS[0][1], topic),
            *[
                (self.WIKI_APIS[1][0], self.WIKI_APIS[1][1], query)
                for query in normalized_queries[:2]
            ],
        ]
        external_links: list[str] = []
        for api_url, source_name, query in wiki_requests:
            wiki_documents, links = self._collect_wikipedia(
                api_url=api_url,
                source_name=source_name,
                topic=query,
            )
            raw_documents.extend(wiki_documents)
            external_links.extend(links)

        for query in [*normalized_queries, topic][:3]:
            raw_documents.extend(self._collect_openalex(query))
            if sum(
                item.get("source_tier") == "academic"
                for item in raw_documents
            ) >= 3:
                break

        for url in external_links[:8]:
            tier = self._classify_url(url)
            if tier not in {"official", "academic", "reference"}:
                continue
            document = self._fetch_web_document(
                url=url,
                fallback_title=topic,
                fallback_source=urlparse(url).netloc,
                published_at="",
                source_tier=tier,
            )
            if document:
                raw_documents.append(document)

        deduplicated: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        for document in raw_documents:
            url = document["source_url"].strip()
            if not url or url in seen_urls or len(document["text"].strip()) < 40:
                continue
            seen_urls.add(url)
            deduplicated.append(document)
            if len(deduplicated) >= 10:
                break

        return [
            SourceDocument(id=f"source_{index}", **document).to_dict()
            for index, document in enumerate(deduplicated, start=1)
        ]

    def _session_get(self, url: str, **kwargs: Any) -> Any:
        if self._get is not None:
            return self._get(url, **kwargs)
        try:
            import requests
        except ImportError as exc:
            raise PublicSourceError("requests 의존성이 설치되지 않았습니다.") from exc
        headers = kwargs.pop("headers", {})
        headers.setdefault(
            "User-Agent",
            "YouTubeAIFactory/8.7 (personal research; contact via GitHub)",
        )
        return requests.get(
            url,
            headers=headers,
            timeout=self._timeout_seconds,
            **kwargs,
        )

    def _collect_wikipedia(
        self,
        *,
        api_url: str,
        source_name: str,
        topic: str,
    ) -> tuple[list[dict[str, str]], list[str]]:
        try:
            search_response = self._session_get(
                api_url,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": topic,
                    "srlimit": 2,
                    "format": "json",
                    "utf8": 1,
                },
            )
            if not getattr(search_response, "ok", False):
                return [], []
            search_data = search_response.json()
        except Exception:
            return [], []

        results = search_data.get("query", {}).get("search", [])
        if not isinstance(results, list):
            return [], []
        documents: list[dict[str, str]] = []
        external_links: list[str] = []
        for result in results[:2]:
            if not isinstance(result, dict):
                continue
            title = str(result.get("title") or "").strip()
            if not title:
                continue
            try:
                page_response = self._session_get(
                    api_url,
                    params={
                        "action": "query",
                        "prop": "extracts|info|extlinks|langlinks",
                        "titles": title,
                        "exintro": 1,
                        "explaintext": 1,
                        "inprop": "url",
                        "ellimit": 50,
                        "lllang": "en",
                        "lllimit": 1,
                        "format": "json",
                        "utf8": 1,
                    },
                )
                if not getattr(page_response, "ok", False):
                    continue
                pages = page_response.json().get("query", {}).get("pages", {})
            except Exception:
                continue
            if not isinstance(pages, dict):
                continue
            for page in pages.values():
                if not isinstance(page, dict):
                    continue
                extract = self._clean_text(str(page.get("extract") or ""))
                full_url = str(page.get("fullurl") or "").strip()
                if extract and full_url:
                    documents.append(
                        {
                            "title": str(page.get("title") or title),
                            "source_name": source_name,
                            "source_url": full_url,
                            "source_tier": "reference",
                            "published_at": "",
                            "text": extract[:5000],
                        }
                    )
                links = page.get("extlinks", [])
                if isinstance(links, list):
                    for item in links:
                        if not isinstance(item, dict):
                            continue
                        url = str(item.get("*") or "").strip()
                        if self._is_http_url(url):
                            external_links.append(url)
                langlinks = page.get("langlinks", [])
                if isinstance(langlinks, list):
                    for item in langlinks:
                        if not isinstance(item, dict) or item.get("lang") != "en":
                            continue
                        english_title = str(item.get("*") or "").strip()
                        if english_title:
                            external_links.insert(
                                0,
                                "https://en.wikipedia.org/wiki/"
                                + quote(english_title.replace(" ", "_")),
                            )
        return documents, external_links

    def _collect_openalex(self, topic: str) -> list[dict[str, str]]:
        try:
            response = self._session_get(
                self.OPENALEX_API,
                params={
                    "search": topic,
                    "per-page": 6,
                    "select": (
                        "id,display_name,publication_year,doi,primary_location,"
                        "abstract_inverted_index"
                    ),
                },
            )
            if not getattr(response, "ok", False):
                return []
            results = response.json().get("results", [])
        except Exception:
            return []
        if not isinstance(results, list):
            return []

        documents: list[dict[str, str]] = []
        for result in results:
            if not isinstance(result, dict):
                continue
            abstract = self._abstract_text(result.get("abstract_inverted_index"))
            title = str(result.get("display_name") or "").strip()
            if not title or len(abstract) < 80:
                continue
            location = result.get("primary_location")
            landing_url = ""
            source_name = "OpenAlex academic record"
            if isinstance(location, dict):
                landing_url = str(location.get("landing_page_url") or "").strip()
                source = location.get("source")
                if isinstance(source, dict):
                    source_name = str(source.get("display_name") or source_name)
            url = landing_url or str(result.get("doi") or result.get("id") or "")
            if not self._is_http_url(url):
                continue
            year = result.get("publication_year")
            documents.append(
                {
                    "title": title,
                    "source_name": source_name,
                    "source_url": url,
                    "source_tier": "academic",
                    "published_at": str(year or ""),
                    "text": abstract[:5000],
                }
            )
            if len(documents) >= 4:
                break
        return documents

    def _fetch_web_document(
        self,
        *,
        url: str,
        fallback_title: str,
        fallback_source: str,
        published_at: str,
        source_tier: str,
    ) -> dict[str, str] | None:
        if not self._is_http_url(url):
            return None
        try:
            response = self._session_get(url, allow_redirects=True)
            if not getattr(response, "ok", False):
                return None
            final_url = str(getattr(response, "url", url) or url)
            content_type = str(getattr(response, "headers", {}).get("Content-Type", ""))
            if "html" not in content_type.casefold():
                return None
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response.text, "html.parser")
            for node in soup(["script", "style", "nav", "footer", "form"]):
                node.decompose()
            title = fallback_title
            if soup.title and soup.title.string:
                title = self._clean_text(soup.title.string) or title
            description = ""
            meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
                "meta", attrs={"property": "og:description"}
            )
            if meta:
                description = str(meta.get("content") or "")
            body_text = self._clean_text(soup.get_text(" ", strip=True))
            text = self._clean_text(f"{description} {body_text}")[:5000]
        except Exception:
            return None
        if len(text) < 40:
            return None
        return {
            "title": title[:300],
            "source_name": fallback_source[:120],
            "source_url": final_url,
            "source_tier": source_tier,
            "published_at": published_at,
            "text": text,
        }

    @staticmethod
    def _abstract_text(value: Any) -> str:
        if not isinstance(value, dict):
            return ""
        positions: list[tuple[int, str]] = []
        for word, indexes in value.items():
            if not isinstance(indexes, list):
                continue
            for index in indexes:
                if isinstance(index, int):
                    positions.append((index, str(word)))
        positions.sort()
        return " ".join(word for _, word in positions)

    @staticmethod
    def _clean_text(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _is_http_url(value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    @staticmethod
    def _classify_url(url: str) -> str:
        domain = urlparse(url).netloc.casefold()
        if any(
            marker in domain
            for marker in (
                ".gov",
                ".go.kr",
                "nasa.gov",
                "noaa.gov",
                "unesco.org",
                "si.edu",
                "britishmuseum.org",
                "loc.gov",
            )
        ):
            return "official"
        if any(
            marker in domain
            for marker in (
                ".edu",
                ".ac.",
                "doi.org",
                "nature.com",
                "science.org",
                "springer.com",
                "sciencedirect.com",
                "jstor.org",
            )
        ):
            return "academic"
        if "wikipedia.org" in domain or "britannica.com" in domain:
            return "reference"
        return "news"
