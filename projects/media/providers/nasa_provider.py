from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests


MEDIA_DIR = Path(__file__).resolve().parents[1]

for module_path in (
    MEDIA_DIR,
    Path(__file__).resolve().parent,
):
    module_path_text = str(module_path)

    if module_path_text not in sys.path:
        sys.path.insert(
            0,
            module_path_text,
        )


from provider_models import (  # noqa: E402
    MediaCandidate,
)


NASA_SEARCH_API_URL = (
    "https://images-api.nasa.gov/search"
)

NASA_ASSET_API_URL = (
    "https://images-api.nasa.gov/asset"
)

DEFAULT_USER_AGENT = (
    "YouTubeContentFactory/7.3 "
    "(NASA media collector; "
    "https://github.com/Eunbi98/"
    "Eunbi98-youtube-content-factory)"
)

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

MIME_BY_EXTENSION = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

BLOCKED_TITLE_TERMS = {
    "logo",
    "icon",
    "insignia",
    "patch",
    "seal",
    "poster",
    "banner",
    "book cover",
    "brochure",
    "infographic",
    "diagram",
    "chart",
    "graph",
    "map",
}

ORIGINAL_MARKERS = (
    "~orig",
    "_orig",
    "-orig",
    "original",
)

SMALL_ASSET_MARKERS = (
    "~small",
    "~medium",
    "~thumb",
    "~preview",
    "_small",
    "_medium",
    "_thumb",
    "_preview",
)


class NasaProviderError(RuntimeError):
    """NASA Images Provider 실행 오류입니다."""


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""

    return re.sub(
        r"\s+",
        " ",
        value,
    ).strip()


def normalize_keyword_list(
    value: object,
) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()

    result: list[str] = []
    seen: set[str] = set()

    for item in value:
        normalized = normalize_text(item)

        if not normalized:
            continue

        identity = normalized.casefold()

        if identity in seen:
            continue

        seen.add(identity)
        result.append(normalized)

    return tuple(result)


def get_file_extension(url: str) -> str:
    path = urlparse(url).path.lower()

    for extension in (
        ".jpeg",
        ".jpg",
        ".png",
        ".webp",
    ):
        if path.endswith(extension):
            return extension

    return Path(path).suffix.lower()


def contains_blocked_title_term(
    title: str,
) -> bool:
    normalized = title.casefold()

    return any(
        term in normalized
        for term in BLOCKED_TITLE_TERMS
    )


def extract_search_tokens(
    query: str,
) -> set[str]:
    return {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            query.casefold(),
        )
        if len(token) >= 2
    }


def choose_preview_url(
    raw_links: object,
) -> str | None:
    if not isinstance(raw_links, list):
        return None

    for raw_link in raw_links:
        if not isinstance(raw_link, dict):
            continue

        href = normalize_text(
            raw_link.get("href")
        )

        render = normalize_text(
            raw_link.get("render")
        ).casefold()

        if href and render == "image":
            return href

    return None


def choose_download_url(
    asset_urls: Iterable[str],
) -> tuple[str, str] | None:
    supported: list[
        tuple[int, str, str]
    ] = []

    for url in asset_urls:
        extension = get_file_extension(url)

        if extension not in SUPPORTED_EXTENSIONS:
            continue

        normalized = url.casefold()
        priority = 50

        if any(
            marker in normalized
            for marker in ORIGINAL_MARKERS
        ):
            priority = 0
        elif any(
            marker in normalized
            for marker in SMALL_ASSET_MARKERS
        ):
            priority = 100
        elif extension in {
            ".jpg",
            ".jpeg",
        }:
            priority = 20
        elif extension == ".png":
            priority = 30
        elif extension == ".webp":
            priority = 40

        supported.append(
            (
                priority,
                url,
                extension,
            )
        )

    if not supported:
        return None

    supported.sort(
        key=lambda item: (
            item[0],
            len(item[1]),
            item[1],
        )
    )

    _, url, extension = supported[0]

    return url, extension


class NasaProvider:
    provider_name = "nasa"

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        user_agent: str = DEFAULT_USER_AGENT,
        session: requests.Session | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise NasaProviderError(
                "timeout_seconds는 0보다 커야 합니다."
            )

        self.timeout_seconds = timeout_seconds
        self.session = (
            session
            or requests.Session()
        )

        self.session.headers.update(
            {
                "User-Agent": user_agent,
                "Accept": "application/json",
            }
        )

    def search(
        self,
        *,
        query: str,
        limit: int = 20,
        page: int = 1,
        year_start: int | None = None,
        year_end: int | None = None,
        allow_blocked_title_terms: bool = False,
    ) -> list[MediaCandidate]:
        normalized_query = normalize_text(
            query
        )

        if not normalized_query:
            raise NasaProviderError(
                "검색어가 비어 있습니다."
            )

        if limit < 1 or limit > 100:
            raise NasaProviderError(
                "limit은 1 이상 100 이하여야 합니다."
            )

        if page < 1:
            raise NasaProviderError(
                "page는 1 이상이어야 합니다."
            )

        if (
            year_start is not None
            and year_end is not None
            and year_start > year_end
        ):
            raise NasaProviderError(
                "year_start는 year_end보다 "
                "클 수 없습니다."
            )

        params: dict[str, str] = {
            "q": normalized_query,
            "media_type": "image",
            "page": str(page),
            "page_size": str(limit),
        }

        if year_start is not None:
            params["year_start"] = str(
                year_start
            )

        if year_end is not None:
            params["year_end"] = str(
                year_end
            )

        payload = self._request_json(
            url=NASA_SEARCH_API_URL,
            params=params,
            context=(
                "NASA 이미지 검색"
            ),
        )

        raw_collection = payload.get(
            "collection"
        )

        if not isinstance(
            raw_collection,
            dict,
        ):
            return []

        raw_items = raw_collection.get(
            "items"
        )

        if not isinstance(raw_items, list):
            return []

        candidates: list[
            MediaCandidate
        ] = []

        for raw_item in raw_items:
            candidate = self._parse_item(
                raw_item=raw_item,
                query=normalized_query,
                allow_blocked_title_terms=(
                    allow_blocked_title_terms
                ),
            )

            if candidate is not None:
                candidates.append(candidate)

        candidates = deduplicate_candidates(
            candidates
        )

        candidates.sort(
            key=lambda item: (
                -item.score,
                item.title.casefold(),
                item.media_id,
            )
        )

        return candidates

    def _parse_item(
        self,
        *,
        raw_item: object,
        query: str,
        allow_blocked_title_terms: bool,
    ) -> MediaCandidate | None:
        if not isinstance(raw_item, dict):
            return None

        raw_data = raw_item.get("data")

        if (
            not isinstance(raw_data, list)
            or not raw_data
            or not isinstance(
                raw_data[0],
                dict,
            )
        ):
            return None

        data = raw_data[0]

        nasa_id = normalize_text(
            data.get("nasa_id")
        )

        title = normalize_text(
            data.get("title")
        )

        description = (
            normalize_text(
                data.get(
                    "description_508"
                )
            )
            or normalize_text(
                data.get("description")
            )
            or None
        )

        if not nasa_id or not title:
            return None

        if (
            not allow_blocked_title_terms
            and contains_blocked_title_term(
                title
            )
        ):
            return None

        preview_url = choose_preview_url(
            raw_item.get("links")
        )

        asset_urls = self._load_asset_urls(
            nasa_id=nasa_id
        )

        selected_asset = (
            choose_download_url(
                asset_urls
            )
        )

        if selected_asset is None:
            return None

        download_url, extension = (
            selected_asset
        )

        source_url = (
            "https://images.nasa.gov/details/"
            f"{nasa_id}"
        )

        center = normalize_text(
            data.get("center")
        )

        photographer = normalize_text(
            data.get("photographer")
        )

        author = (
            photographer
            or center
            or "NASA"
        )

        keywords = normalize_keyword_list(
            data.get("keywords")
        )

        date_created = normalize_text(
            data.get("date_created")
        )

        score = self._calculate_base_score(
            query=query,
            title=title,
            description=(
                description or ""
            ),
            keywords=keywords,
            center=center,
            date_created=date_created,
        )

        return MediaCandidate(
            provider=self.provider_name,
            media_id=nasa_id,
            title=title,
            query=query,
            media_type="image",
            mime_type=MIME_BY_EXTENSION[
                extension
            ],
            source_url=source_url,
            download_url=download_url,
            thumbnail_url=preview_url,
            author=author,
            author_url=None,
            license_name=(
                "NASA Media Usage Guidelines"
            ),
            license_url=(
                "https://www.nasa.gov/"
                "nasa-brand-center/"
                "images-and-media/"
            ),
            width=0,
            height=0,
            orientation="unknown",
            file_extension=extension,
            description=description,
            score=score,
        )

    def _load_asset_urls(
        self,
        *,
        nasa_id: str,
    ) -> list[str]:
        payload = self._request_json(
            url=(
                f"{NASA_ASSET_API_URL}/"
                f"{nasa_id}"
            ),
            params=None,
            context=(
                "NASA 원본 자산 조회"
            ),
        )

        raw_collection = payload.get(
            "collection"
        )

        if not isinstance(
            raw_collection,
            dict,
        ):
            return []

        raw_items = raw_collection.get(
            "items"
        )

        if not isinstance(raw_items, list):
            return []

        urls: list[str] = []

        for raw_item in raw_items:
            if not isinstance(
                raw_item,
                dict,
            ):
                continue

            href = normalize_text(
                raw_item.get("href")
            )

            if href:
                urls.append(href)

        return urls

    def _request_json(
        self,
        *,
        url: str,
        params: dict[str, str] | None,
        context: str,
    ) -> dict[str, Any]:
        try:
            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise NasaProviderError(
                f"{context} 요청에 실패했습니다.\n"
                f"주소: {url}\n"
                f"원인: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise NasaProviderError(
                f"{context} 응답이 JSON 형식이 "
                "아닙니다."
            ) from exc

        if not isinstance(payload, dict):
            raise NasaProviderError(
                f"{context} 응답 최상위 형식이 "
                "올바르지 않습니다."
            )

        return payload

    @staticmethod
    def _calculate_base_score(
        *,
        query: str,
        title: str,
        description: str,
        keywords: tuple[str, ...],
        center: str,
        date_created: str,
    ) -> float:
        query_tokens = extract_search_tokens(
            query
        )

        title_text = title.casefold()

        combined = " ".join(
            (
                title,
                description,
                *keywords,
            )
        ).casefold()

        title_matches = sum(
            1
            for token in query_tokens
            if token in title_text
        )

        combined_matches = sum(
            1
            for token in query_tokens
            if token in combined
        )

        score = (
            title_matches * 24.0
            + combined_matches * 10.0
        )

        if keywords:
            score += min(
                len(keywords),
                10,
            ) * 0.5

        if center:
            score += 3.0

        if date_created:
            score += 2.0

        return round(score, 3)


def deduplicate_candidates(
    candidates: Iterable[
        MediaCandidate
    ],
) -> list[MediaCandidate]:
    result: list[MediaCandidate] = []
    seen: set[
        tuple[str, str]
    ] = set()

    for candidate in candidates:
        identity = (
            candidate.provider,
            candidate.media_id,
        )

        if identity in seen:
            continue

        seen.add(identity)
        result.append(candidate)

    return result


def save_candidates(
    *,
    candidates: list[
        MediaCandidate
    ],
    output_path: Path,
    query: str,
) -> None:
    resolved_path = (
        output_path.resolve()
    )

    resolved_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "version": "7.3",
        "provider": "nasa",
        "query": query,
        "candidateCount": len(
            candidates
        ),
        "candidates": [
            candidate.to_dict()
            for candidate in candidates
        ],
    }

    temporary_path = (
        resolved_path.with_suffix(
            f"{resolved_path.suffix}.tmp"
        )
    )

    try:
        temporary_path.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
            ) + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(
            resolved_path
        )
    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink()

        raise NasaProviderError(
            "검색 결과 저장에 실패했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc


def build_argument_parser() -> (
    argparse.ArgumentParser
):
    parser = argparse.ArgumentParser(
        description=(
            "NASA Image and Video Library에서 "
            "원본 이미지 후보를 수집합니다."
        )
    )

    parser.add_argument(
        "--query",
        required=True,
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=20,
    )

    parser.add_argument(
        "--page",
        type=int,
        default=1,
    )

    parser.add_argument(
        "--year-start",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--year-end",
        type=int,
        default=None,
    )

    parser.add_argument(
        "--output",
        default=None,
    )

    parser.add_argument(
        "--allow-blocked-title-terms",
        action="store_true",
    )

    return parser


def print_summary(
    *,
    query: str,
    candidates: list[
        MediaCandidate
    ],
) -> None:
    print("=" * 72)
    print(
        " YouTube Content Factory "
        "Release 7.3 NASA Provider"
    )
    print("=" * 72)

    print(
        f"{'query':>18}: {query}"
    )

    print(
        f"{'candidate_count':>18}: "
        f"{len(candidates)}"
    )

    print("-" * 72)

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        print(
            f"[{index:02d}] "
            f"{candidate.score:6.1f} "
            f"{candidate.media_id} "
            f"{candidate.title}"
        )

        print(
            f"     type   : "
            f"{candidate.mime_type}"
        )

        print(
            f"     author : "
            f"{candidate.author or 'NASA'}"
        )

        print(
            f"     source : "
            f"{candidate.source_url}"
        )

    print("-" * 72)

    print(
        "[성공] NASA 후보 수집 완료"
    )


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    try:
        provider = NasaProvider()

        candidates = provider.search(
            query=arguments.query,
            limit=arguments.limit,
            page=arguments.page,
            year_start=(
                arguments.year_start
            ),
            year_end=(
                arguments.year_end
            ),
            allow_blocked_title_terms=(
                arguments
                .allow_blocked_title_terms
            ),
        )

        if arguments.output:
            save_candidates(
                candidates=candidates,
                output_path=Path(
                    arguments.output
                ),
                query=arguments.query,
            )

    except (
        NasaProviderError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )
        return 1

    print_summary(
        query=arguments.query,
        candidates=candidates,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())