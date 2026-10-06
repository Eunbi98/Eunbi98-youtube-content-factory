from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import requests

from provider_models import MediaCandidate, infer_orientation


PIXABAY_API_URL = "https://pixabay.com/api/"
PIXABAY_LICENSE_NAME = "Pixabay Content License"
PIXABAY_LICENSE_URL = "https://pixabay.com/service/license-summary/"


class PixabayProviderError(RuntimeError):
    pass


def _text(value: object) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _integer(value: object) -> int:
    if isinstance(value, bool):
        return 0

    if isinstance(value, int):
        return value

    if isinstance(value, float):
        return int(value)

    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0

    return 0


def _extension(url: str) -> str:
    suffix = Path(
        urlparse(url).path
    ).suffix.lower()

    if suffix in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        return suffix

    return ".jpg"


def _mime_type(extension: str) -> str:
    mapping = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return mapping.get(
        extension,
        "image/jpeg",
    )


class PixabayProvider:
    provider_name = "pixabay"

    def __init__(
        self,
        *,
        api_key: str,
        timeout_seconds: float = 20.0,
        session: requests.Session | None = None,
    ) -> None:
        normalized_api_key = api_key.strip()

        if not normalized_api_key:
            raise PixabayProviderError(
                "PIXABAY_API_KEY is empty."
            )

        if timeout_seconds <= 0:
            raise PixabayProviderError(
                "timeout_seconds must be positive."
            )

        self.api_key = normalized_api_key
        self.timeout_seconds = timeout_seconds
        self.session = (
            session
            or requests.Session()
        )

        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": (
                    "youtube-content-factory/1.0"
                ),
            }
        )

    def search(
        self,
        *,
        query: str,
        limit: int = 20,
        min_width: int = 1080,
        min_height: int = 1080,
    ) -> list[MediaCandidate]:
        normalized_query = query.strip()

        if not normalized_query:
            return []

        normalized_limit = max(
            3,
            min(limit, 50),
        )

        params = {
            "key": self.api_key,
            "q": normalized_query,
            "lang": "en",
            "image_type": "photo",
            "orientation": "all",
            "category": "",
            "min_width": min_width,
            "min_height": min_height,
            "safesearch": "true",
            "order": "popular",
            "page": 1,
            "per_page": normalized_limit,
        }

        try:
            response = self.session.get(
                PIXABAY_API_URL,
                params=params,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise PixabayProviderError(
                "Pixabay API request failed.\n"
                f"query: {normalized_query}\n"
                f"reason: {exc}"
            ) from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise PixabayProviderError(
                "Pixabay response is not JSON."
            ) from exc

        if not isinstance(payload, dict):
            return []

        raw_hits = payload.get("hits")

        if not isinstance(raw_hits, list):
            return []

        candidates: list[MediaCandidate] = []

        for raw_hit in raw_hits:
            candidate = self._parse_hit(
                raw_hit=raw_hit,
                query=normalized_query,
                min_width=min_width,
                min_height=min_height,
            )

            if candidate is not None:
                candidates.append(candidate)

        candidates.sort(
            key=lambda item: (
                -item.score,
                -(item.width * item.height),
                item.title.casefold(),
            )
        )

        return candidates

    def _parse_hit(
        self,
        *,
        raw_hit: object,
        query: str,
        min_width: int,
        min_height: int,
    ) -> MediaCandidate | None:
        if not isinstance(raw_hit, dict):
            return None

        media_id = str(
            _integer(raw_hit.get("id"))
        )

        if media_id == "0":
            return None

        download_url = (
            _text(raw_hit.get("largeImageURL"))
            or _text(raw_hit.get("webformatURL"))
            or _text(raw_hit.get("previewURL"))
        )

        if not download_url:
            return None

        width = _integer(
            raw_hit.get("imageWidth")
        )
        height = _integer(
            raw_hit.get("imageHeight")
        )

        if width <= 0:
            width = _integer(
                raw_hit.get("webformatWidth")
            )

        if height <= 0:
            height = _integer(
                raw_hit.get("webformatHeight")
            )

        if (
            width < min_width
            or height < min_height
        ):
            return None

        tags = _text(raw_hit.get("tags"))
        title = (
            tags
            or f"Pixabay image {media_id}"
        )

        source_url = (
            _text(raw_hit.get("pageURL"))
            or download_url
        )
        thumbnail_url = (
            _text(raw_hit.get("previewURL"))
            or None
        )

        author = (
            _text(raw_hit.get("user"))
            or None
        )
        user_id = _integer(
            raw_hit.get("user_id")
        )

        author_url: str | None = None

        if author and user_id > 0:
            normalized_author = (
                author.lower()
                .replace(" ", "-")
            )
            author_url = (
                "https://pixabay.com/users/"
                f"{normalized_author}-{user_id}/"
            )

        extension = _extension(
            download_url
        )

        likes = _integer(
            raw_hit.get("likes")
        )
        downloads = _integer(
            raw_hit.get("downloads")
        )
        views = _integer(
            raw_hit.get("views")
        )

        score = 20.0
        score += min(
            likes / 100.0,
            10.0,
        )
        score += min(
            downloads / 10000.0,
            10.0,
        )
        score += min(
            views / 100000.0,
            5.0,
        )
        score += min(
            (width * height)
            / 1_000_000.0,
            10.0,
        )

        return MediaCandidate(
            provider=self.provider_name,
            media_id=media_id,
            title=title,
            query=query,
            media_type="image",
            mime_type=_mime_type(
                extension
            ),
            source_url=source_url,
            download_url=download_url,
            thumbnail_url=thumbnail_url,
            author=author,
            author_url=author_url,
            license_name=(
                PIXABAY_LICENSE_NAME
            ),
            license_url=(
                PIXABAY_LICENSE_URL
            ),
            width=width,
            height=height,
            orientation=infer_orientation(
                width,
                height,
            ),
            file_extension=extension,
            description=tags or None,
            score=round(score, 4),
        )
