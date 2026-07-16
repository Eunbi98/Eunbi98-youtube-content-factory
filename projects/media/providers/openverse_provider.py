from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

import requests

from provider_models import MediaCandidate, infer_orientation


OPENVERSE_API_URL = (
    "https://api.openverse.org/v1/images/"
)


class OpenverseProviderError(RuntimeError):
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


def _extension(
    url: str,
    raw_extension: object,
) -> str:
    extension = _text(
        raw_extension
    ).lower()

    if extension:
        if not extension.startswith("."):
            extension = f".{extension}"

        if extension in {
            ".jpg",
            ".jpeg",
            ".png",
            ".webp",
        }:
            return extension

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


def _mime_type(
    extension: str,
) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(
        extension,
        "image/jpeg",
    )


class OpenverseProvider:
    provider_name = "openverse"

    def __init__(
        self,
        *,
        timeout_seconds: float = 20.0,
        session: requests.Session | None = None,
    ) -> None:
        if timeout_seconds <= 0:
            raise OpenverseProviderError(
                "timeout_seconds must be positive."
            )

        self.timeout_seconds = timeout_seconds
        self.session = (
            session
            or requests.Session()
        )

        self.session.headers.update(
            {
                "Accept": "application/json",
                "User-Agent": (
                    "youtube-content-factory/1.0 "
                    "(media research)"
                ),
            }
        )

    def search(
        self,
        *,
        query: str,
        limit: int = 20,
        min_width: int = 640,
        min_height: int = 480,
    ) -> list[MediaCandidate]:
        normalized_query = query.strip()

        if not normalized_query:
            return []

        normalized_limit = max(
            1,
            min(limit, 50),
        )

        params = {
            "q": normalized_query,
            "page_size": normalized_limit,
            "mature": "false",
        }

        try:
            response = self.session.get(
                OPENVERSE_API_URL,
                params=params,
                timeout=self.timeout_seconds,
            )

            if response.status_code == 429:
                print(
                    "[WARN] Openverse request "
                    "rate limited."
                )
                return []

            response.raise_for_status()
        except requests.RequestException as exc:
            print(
                "[WARN] Openverse search failed: "
                f"{exc}"
            )
            return []

        try:
            payload = response.json()
        except ValueError:
            print(
                "[WARN] Openverse response "
                "is not JSON."
            )
            return []

        if not isinstance(payload, dict):
            return []

        raw_results = payload.get(
            "results"
        )

        if not isinstance(
            raw_results,
            list,
        ):
            return []

        candidates: list[
            MediaCandidate
        ] = []

        for raw_result in raw_results:
            candidate = self._parse_result(
                raw_result=raw_result,
                query=normalized_query,
                min_width=min_width,
                min_height=min_height,
            )

            if candidate is not None:
                candidates.append(
                    candidate
                )

        candidates.sort(
            key=lambda item: (
                -item.score,
                -(
                    item.width
                    * item.height
                ),
                item.title.casefold(),
            )
        )

        return candidates

    def _parse_result(
        self,
        *,
        raw_result: object,
        query: str,
        min_width: int,
        min_height: int,
    ) -> MediaCandidate | None:
        if not isinstance(
            raw_result,
            dict,
        ):
            return None

        media_id = _text(
            raw_result.get("id")
        )

        if not media_id:
            return None

        download_url = _text(
            raw_result.get("url")
        )

        thumbnail_url_text = _text(
            raw_result.get("thumbnail")
        )

        if (
            "upload.wikimedia.org"
            in download_url.casefold()
            and thumbnail_url_text
        ):
            download_url = thumbnail_url_text

        if not download_url:
            return None

        width = _integer(
            raw_result.get("width")
        )
        height = _integer(
            raw_result.get("height")
        )

        if (
            width <= 0
            or height <= 0
        ):
            return None

        if (
            width < min_width
            or height < min_height
        ):
            return None

        title = (
            _text(
                raw_result.get("title")
            )
            or f"Openverse image {media_id}"
        )

        source_url = (
            _text(
                raw_result.get(
                    "foreign_landing_url"
                )
            )
            or download_url
        )

        thumbnail_url = (
            _text(
                raw_result.get(
                    "thumbnail"
                )
            )
            or None
        )

        author = (
            _text(
                raw_result.get("creator")
            )
            or None
        )

        author_url = (
            _text(
                raw_result.get(
                    "creator_url"
                )
            )
            or None
        )

        license_code = _text(
            raw_result.get("license")
        )
        license_version = _text(
            raw_result.get(
                "license_version"
            )
        )

        license_name_parts = [
            value
            for value in (
                license_code.upper(),
                license_version,
            )
            if value
        ]

        license_name = (
            " ".join(
                license_name_parts
            )
            or None
        )

        license_url = (
            _text(
                raw_result.get(
                    "license_url"
                )
            )
            or None
        )

        extension = _extension(
            download_url,
            raw_result.get("extension"),
        )

        description = (
            _text(
                raw_result.get("tags")
            )
            or _text(
                raw_result.get(
                    "source"
                )
            )
            or None
        )

        score = 18.0
        score += min(
            (
                width
                * height
            )
            / 1_000_000.0,
            12.0,
        )

        if thumbnail_url:
            score += 1.0

        if license_url:
            score += 2.0

        if author:
            score += 1.0

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
            license_name=license_name,
            license_url=license_url,
            width=width,
            height=height,
            orientation=infer_orientation(
                width,
                height,
            ),
            file_extension=extension,
            description=description,
            score=round(
                score,
                4,
            ),
        )
