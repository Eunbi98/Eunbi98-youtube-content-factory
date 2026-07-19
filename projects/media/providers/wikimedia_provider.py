from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

import requests


MEDIA_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = MEDIA_DIR.parents[1]

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
    infer_orientation,
)


WIKIMEDIA_API_URL = (
    "https://commons.wikimedia.org/w/api.php"
)

DEFAULT_USER_AGENT = (
    "YouTubeContentFactory/7.2 "
    "(Wikimedia media collector; "
    "https://github.com/Eunbi98/"
    "Eunbi98-youtube-content-factory)"
)

SUPPORTED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

SUPPORTED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}

BLOCKED_TITLE_TERMS = {
    "logo",
    "icon",
    "symbol",
    "diagram",
    "map",
    "flag",
    "coat of arms",
    "seal",
    "signature",
    "poster",
    "advertisement",
    "book cover",
    "album cover",
    "screenshot",
}

ALLOWED_LICENSE_PATTERNS = (
    re.compile(
        r"public\s*domain",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bcc0\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"creative\s*commons"
        r".*\bby(?:-sa)?\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\bcc\s*by(?:-sa)?\b",
        flags=re.IGNORECASE,
    ),
)

BLOCKED_LICENSE_PATTERNS = (
    re.compile(
        r"\b(?:nc|noncommercial)\b",
        flags=re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:nd|noderivatives)\b",
        flags=re.IGNORECASE,
    ),
)


class WikimediaProviderError(RuntimeError):
    """Wikimedia Provider 실행 오류입니다."""


def normalize_text(value: object) -> str:
    if not isinstance(value, str):
        return ""

    cleaned = html.unescape(value)
    cleaned = re.sub(
        r"<[^>]+>",
        " ",
        cleaned,
    )
    cleaned = re.sub(
        r"\s+",
        " ",
        cleaned,
    )

    return cleaned.strip()


def get_metadata_value(
    metadata: dict[str, Any],
    key: str,
) -> str:
    raw_value = metadata.get(key)

    if not isinstance(raw_value, dict):
        return ""

    return normalize_text(
        raw_value.get("value")
    )


def get_file_extension(
    url: str,
) -> str:
    parsed = urlparse(url)
    path = parsed.path.lower()

    for extension in (
        ".jpeg",
        ".jpg",
        ".png",
        ".webp",
    ):
        if path.endswith(extension):
            return extension

    return Path(path).suffix.lower()


def is_license_allowed(
    license_name: str,
    usage_terms: str,
) -> bool:
    combined = " ".join(
        value
        for value in (
            license_name,
            usage_terms,
        )
        if value
    )

    if not combined:
        return False

    if any(
        pattern.search(combined)
        for pattern in BLOCKED_LICENSE_PATTERNS
    ):
        return False

    return any(
        pattern.search(combined)
        for pattern in ALLOWED_LICENSE_PATTERNS
    )


def contains_blocked_title_term(
    title: str,
) -> bool:
    normalized = title.casefold()

    return any(
        term in normalized
        for term in BLOCKED_TITLE_TERMS
    )


def build_search_term(
    query: str,
) -> str:
    normalized = normalize_text(query)

    if not normalized:
        raise WikimediaProviderError(
            "검색어가 비어 있습니다."
        )

    if normalized.casefold().startswith(
        "file:"
    ):
        return normalized

    return f"file:{normalized}"


class WikimediaProvider:
    provider_name = "wikimedia"

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        user_agent: str = DEFAULT_USER_AGENT,
        session: requests.Session | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise WikimediaProviderError(
                "timeout_seconds는 0보다 커야 합니다."
            )

        self.timeout_seconds = timeout_seconds
        self.session = session or requests.Session()

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
        min_width: int = 1080,
        min_height: int = 1080,
        allow_blocked_title_terms: bool = False,
    ) -> list[MediaCandidate]:
        if limit < 1 or limit > 50:
            raise WikimediaProviderError(
                "limit은 1 이상 50 이하여야 합니다."
            )

        if min_width < 0 or min_height < 0:
            raise WikimediaProviderError(
                "최소 크기는 0 이상이어야 합니다."
            )

        search_term = build_search_term(query)

        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "generator": "search",
            "gsrnamespace": "6",
            "gsrsearch": search_term,
            "gsrlimit": str(limit),
            "prop": "imageinfo",
            "iiprop": (
                "url|size|mime|extmetadata"
            ),
            "iiurlwidth": "1080",
            "origin": "*",
        }

        try:
            response = self.session.get(
                WIKIMEDIA_API_URL,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise WikimediaProviderError(
                "Wikimedia API 요청에 실패했습니다.\n"
                f"검색어: {query}\n"
                f"원인: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise WikimediaProviderError(
                "Wikimedia API 응답이 JSON 형식이 "
                "아닙니다."
            ) from exc

        if not isinstance(payload, dict):
            raise WikimediaProviderError(
                "Wikimedia API 응답 최상위 형식이 "
                "올바르지 않습니다."
            )

        raw_query = payload.get("query")

        if not isinstance(raw_query, dict):
            return []

        raw_pages = raw_query.get("pages")

        if not isinstance(raw_pages, list):
            return []

        candidates: list[MediaCandidate] = []

        for raw_page in raw_pages:
            candidate = self._parse_page(
                raw_page=raw_page,
                query=query,
                min_width=min_width,
                min_height=min_height,
                allow_blocked_title_terms=(
                    allow_blocked_title_terms
                ),
            )

            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                -item.score,
                -item.width * item.height,
                item.title.casefold(),
            )
        )

        return candidates

    def _parse_page(
        self,
        *,
        raw_page: object,
        query: str,
        min_width: int,
        min_height: int,
        allow_blocked_title_terms: bool,
    ) -> MediaCandidate | None:
        if not isinstance(raw_page, dict):
            return None

        title = normalize_text(
            raw_page.get("title")
        )

        if not title:
            return None

        if (
            not allow_blocked_title_terms
            and contains_blocked_title_term(title)
        ):
            return None

        raw_image_info = raw_page.get(
            "imageinfo"
        )

        if (
            not isinstance(raw_image_info, list)
            or not raw_image_info
            or not isinstance(
                raw_image_info[0],
                dict,
            )
        ):
            return None

        image_info = raw_image_info[0]

        mime_type = normalize_text(
            image_info.get("mime")
        ).casefold()

        if mime_type not in SUPPORTED_MIME_TYPES:
            return None

        download_url = normalize_text(
            image_info.get("url")
        )

        source_url = normalize_text(
            image_info.get("descriptionurl")
        )

        thumbnail_url = normalize_text(
            image_info.get("thumburl")
        ) or None

        if thumbnail_url:
            download_url = thumbnail_url

        if not download_url or not source_url:
            return None

        extension = get_file_extension(
            download_url
        )

        if extension not in SUPPORTED_EXTENSIONS:
            return None

        width = int(
            image_info.get("width") or 0
        )
        height = int(
            image_info.get("height") or 0
        )

        if (
            width < min_width
            or height < min_height
        ):
            return None

        raw_metadata = image_info.get(
            "extmetadata"
        )

        metadata = (
            raw_metadata
            if isinstance(raw_metadata, dict)
            else {}
        )

        license_name = (
            get_metadata_value(
                metadata,
                "LicenseShortName",
            )
            or get_metadata_value(
                metadata,
                "UsageTerms",
            )
        )

        usage_terms = get_metadata_value(
            metadata,
            "UsageTerms",
        )

        if not is_license_allowed(
            license_name,
            usage_terms,
        ):
            return None

        license_url = (
            get_metadata_value(
                metadata,
                "LicenseUrl",
            )
            or None
        )

        author = (
            get_metadata_value(
                metadata,
                "Artist",
            )
            or get_metadata_value(
                metadata,
                "Credit",
            )
            or None
        )

        author_url = (
            get_metadata_value(
                metadata,
                "AttributionRequired",
            )
            or None
        )

        description = (
            get_metadata_value(
                metadata,
                "ImageDescription",
            )
            or get_metadata_value(
                metadata,
                "ObjectName",
            )
            or None
        )

        media_id = str(
            raw_page.get("pageid") or title
        )

        score = self._calculate_base_score(
            query=query,
            title=title,
            description=description or "",
            width=width,
            height=height,
        )

        return MediaCandidate(
            provider=self.provider_name,
            media_id=media_id,
            title=title,
            query=query,
            media_type="image",
            mime_type=mime_type,
            source_url=source_url,
            download_url=download_url,
            thumbnail_url=thumbnail_url,
            author=author,
            author_url=author_url,
            license_name=license_name or None,
            license_url=license_url,
            width=width,
            height=height,
            orientation=infer_orientation(
                width,
                height,
            ),
            file_extension=extension,
            description=description,
            score=score,
        )

    @staticmethod
    def _calculate_base_score(
        *,
        query: str,
        title: str,
        description: str,
        width: int,
        height: int,
    ) -> float:
        query_tokens = {
            token
            for token in re.findall(
                r"[a-z0-9]+",
                query.casefold(),
            )
            if len(token) >= 2
        }

        haystack = (
            f"{title} {description}"
        ).casefold()

        matched_tokens = sum(
            1
            for token in query_tokens
            if token in haystack
        )

        score = matched_tokens * 20.0

        pixel_count = width * height

        if pixel_count >= 12_000_000:
            score += 20.0
        elif pixel_count >= 6_000_000:
            score += 14.0
        elif pixel_count >= 3_000_000:
            score += 8.0
        else:
            score += 3.0

        if height > width:
            score += 8.0
        elif height == width:
            score += 4.0

        return round(score, 3)


def deduplicate_candidates(
    candidates: Iterable[MediaCandidate],
) -> list[MediaCandidate]:
    result: list[MediaCandidate] = []
    seen: set[tuple[str, str]] = set()

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
    candidates: list[MediaCandidate],
    output_path: Path,
    query: str,
) -> None:
    resolved_path = output_path.resolve()
    resolved_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    payload = {
        "version": "7.2",
        "provider": "wikimedia",
        "query": query,
        "candidateCount": len(candidates),
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

        raise WikimediaProviderError(
            "검색 결과 저장에 실패했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Wikimedia Commons에서 "
            "라이선스와 해상도를 검증한 "
            "이미지 후보를 수집합니다."
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
        "--min-width",
        type=int,
        default=1080,
    )

    parser.add_argument(
        "--min-height",
        type=int,
        default=1080,
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
    candidates: list[MediaCandidate],
) -> None:
    print("=" * 72)
    print(
        " YouTube Content Factory "
        "Release 7.2 Wikimedia Provider"
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
            f"{candidate.orientation:<9} "
            f"{candidate.width}x{candidate.height} "
            f"{candidate.title}"
        )
        print(
            f"     license: "
            f"{candidate.license_name or 'unknown'}"
        )
        print(
            f"     source : "
            f"{candidate.source_url}"
        )

    print("-" * 72)
    print(
        "[성공] Wikimedia 후보 수집 완료"
    )


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    try:
        provider = WikimediaProvider()

        candidates = provider.search(
            query=arguments.query,
            limit=arguments.limit,
            min_width=arguments.min_width,
            min_height=arguments.min_height,
            allow_blocked_title_terms=(
                arguments
                .allow_blocked_title_terms
            ),
        )

        candidates = deduplicate_candidates(
            candidates
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
        WikimediaProviderError,
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
