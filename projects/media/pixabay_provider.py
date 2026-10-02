from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Any, Final
from urllib.parse import quote

from dotenv import load_dotenv

from base_provider import (
    MediaCandidate,
    MediaDownloadResult,
    MediaKind,
    MediaProvider,
    MediaProviderError,
    MediaSearchRequest,
)
from http_client import (
    HttpClient,
    HttpClientError,
    build_config_from_environment,
)


PIXABAY_API_URL: Final[str] = (
    "https://pixabay.com/api/"
)

PIXABAY_LICENSE_NAME: Final[str] = (
    "Pixabay Content License"
)

PIXABAY_LICENSE_URL: Final[str] = (
    "https://pixabay.com/service/license-summary/"
)


class PixabayProviderError(
    MediaProviderError
):
    """Pixabay 寃???먮뒗 ?ㅼ슫濡쒕뱶 ?ㅻ쪟?낅땲??"""


def normalize_string(
    value: object,
) -> str | None:
    if not isinstance(
        value,
        str,
    ):
        return None

    normalized = " ".join(
        value
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )

    return normalized or None


def parse_int(
    value: object,
    *,
    default: int = 0,
) -> int:
    if isinstance(
        value,
        bool,
    ):
        return default

    if isinstance(
        value,
        int,
    ):
        return value

    if isinstance(
        value,
        float,
    ):
        return int(value)

    if isinstance(
        value,
        str,
    ):
        try:
            return int(
                value.strip()
            )
        except ValueError:
            return default

    return default


def build_author_url(
    *,
    username: str | None,
    user_id: int,
) -> str | None:
    if (
        not username
        or user_id <= 0
    ):
        return None

    normalized_username = quote(
        username.replace(
            " ",
            "-",
        ),
        safe="-_",
    )

    return (
        "https://pixabay.com/users/"
        f"{normalized_username}-{user_id}/"
    )


def infer_extension(
    url: str,
) -> str | None:
    clean_url = (
        url.split(
            "?",
            maxsplit=1,
        )[0]
    )

    suffix = Path(
        clean_url
    ).suffix

    if not suffix:
        return None

    extension = (
        suffix
        .lower()
        .lstrip(".")
    )

    if extension == "jpeg":
        return "jpg"

    return extension or None


def map_orientation(
    orientation: str,
) -> str:
    mapping = {
        "portrait": "vertical",
        "landscape": "horizontal",
        "square": "all",
        "any": "all",
    }

    return mapping[
        orientation
    ]


class PixabayProvider(
    MediaProvider
):
    """
    Pixabay 怨듭떇 API 湲곕컲 ?대?吏 Provider?낅땲??
    """

    def __init__(
        self,
        *,
        api_key: str | None = None,
        http_client: HttpClient | None = None,
        language: str = "en",
        image_type: str = "photo",
        order: str = "popular",
    ) -> None:
        load_dotenv()

        resolved_api_key = (
            api_key
            or os.getenv(
                "PIXABAY_API_KEY"
            )
            or ""
        ).strip()

        if not resolved_api_key:
            raise PixabayProviderError(
                "PIXABAY_API_KEY媛 ?놁뒿?덈떎.\n"
                "?꾨줈?앺듃 猷⑦듃??.env ?뚯씪??"
                "?ㅼ쓬 ?뺤떇?쇰줈 異붽??섏꽭??\n"
                "PIXABAY_API_KEY=your_key"
            )

        normalized_language = (
            language.strip().lower()
        )

        if not normalized_language:
            raise ValueError(
                "language??鍮꾩뼱 ?덉쓣 ???놁뒿?덈떎."
            )

        if image_type not in {
            "all",
            "photo",
            "illustration",
            "vector",
        }:
            raise ValueError(
                "吏?먰븯吏 ?딅뒗 image_type?낅땲?? "
                f"{image_type}"
            )

        if order not in {
            "popular",
            "latest",
        }:
            raise ValueError(
                "吏?먰븯吏 ?딅뒗 order?낅땲?? "
                f"{order}"
            )

        self._api_key = (
            resolved_api_key
        )

        self._language = (
            normalized_language
        )

        self._image_type = (
            image_type
        )

        self._order = order

        self._http_client = (
            http_client
            if http_client is not None
            else HttpClient(
                build_config_from_environment()
            )
        )

        self._owns_http_client = (
            http_client is None
        )

    @property
    def name(
        self,
    ) -> str:
        return "pixabay"

    @property
    def supported_media_kinds(
        self,
    ) -> frozenset[MediaKind]:
        return frozenset({
            "image",
        })

    def close(
        self,
    ) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def __enter__(
        self,
    ) -> "PixabayProvider":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    def search(
        self,
        request: MediaSearchRequest,
    ) -> list[MediaCandidate]:
        self.validate_request(
            request
        )

        query = request.query[:100]

        per_page = min(
            200,
            max(
                3,
                request.max_results * 3,
            ),
        )

        params: dict[str, object] = {
            "key": self._api_key,
            "q": query,
            "lang": self._language,
            "image_type": (
                self._image_type
            ),
            "orientation": (
                map_orientation(
                    request.orientation
                )
            ),
            "min_width": (
                request.min_width
            ),
            "min_height": (
                request.min_height
            ),
            "safesearch": (
                str(
                    request.safe_search
                ).lower()
            ),
            "order": self._order,
            "page": 1,
            "per_page": per_page,
        }

        try:
            payload = (
                self._http_client.get_json(
                    PIXABAY_API_URL,
                    params=params,
                )
            )

        except (
            HttpClientError,
            ValueError,
        ) as exc:
            raise PixabayProviderError(
                "Pixabay ?대?吏 寃?됱뿉 "
                "?ㅽ뙣?덉뒿?덈떎.\n"
                f"寃?됱뼱: {request.query}\n"
                f"?먯씤: {exc}"
            ) from exc

        candidates = (
            self._parse_search_response(
                payload
            )
        )

        return self.filter_candidates(
            request=request,
            candidates=candidates,
        )

    def download(
        self,
        *,
        candidate: MediaCandidate,
        output_path: Path,
        overwrite: bool = False,
    ) -> MediaDownloadResult:
        if (
            candidate.provider
            != self.name
        ):
            raise PixabayProviderError(
                "?ㅻⅨ Provider???꾨낫??"
                "PixabayProvider濡?"
                "?ㅼ슫濡쒕뱶?????놁뒿?덈떎.\n"
                f"candidate.provider: "
                f"{candidate.provider}"
            )

        if (
            candidate.media_kind
            != "image"
        ):
            raise PixabayProviderError(
                "PixabayProvider???꾩옱 "
                "?대?吏 ?ㅼ슫濡쒕뱶留?吏?먰빀?덈떎."
            )

        try:
            result = (
                self._http_client.download(
                    url=(
                        candidate.download_url
                    ),
                    output_path=output_path,
                    overwrite=overwrite,
                    minimum_size_bytes=1024,
                    show_progress=True,
                )
            )

        except (
            HttpClientError,
            ValueError,
            OSError,
        ) as exc:
            raise PixabayProviderError(
                "Pixabay ?대?吏 ?ㅼ슫濡쒕뱶??"
                "?ㅽ뙣?덉뒿?덈떎.\n"
                f"?쒕ぉ: {candidate.title}\n"
                f"URL: "
                f"{candidate.download_url}\n"
                f"?먯씤: {exc}"
            ) from exc

        return MediaDownloadResult(
            candidate=candidate,
            output_path=(
                result.output_path
            ),
            file_size_bytes=(
                result.file_size_bytes
            ),
        )

    def _parse_search_response(
        self,
        payload: dict[str, Any],
    ) -> list[MediaCandidate]:
        raw_hits = payload.get(
            "hits"
        )

        if not isinstance(
            raw_hits,
            list,
        ):
            return []

        candidates: list[
            MediaCandidate
        ] = []

        for raw_hit in raw_hits:
            if not isinstance(
                raw_hit,
                dict,
            ):
                continue

            candidate = (
                self._parse_hit(
                    raw_hit
                )
            )

            if candidate is not None:
                candidates.append(
                    candidate
                )

        return candidates

    def _parse_hit(
        self,
        raw_hit: dict[str, Any],
    ) -> MediaCandidate | None:
        media_id = parse_int(
            raw_hit.get("id")
        )

        if media_id <= 0:
            return None

        source_url = normalize_string(
            raw_hit.get("pageURL")
        )

        if not source_url:
            return None

        download_url = (
            normalize_string(
                raw_hit.get(
                    "imageURL"
                )
            )
            or normalize_string(
                raw_hit.get(
                    "fullHDURL"
                )
            )
            or normalize_string(
                raw_hit.get(
                    "largeImageURL"
                )
            )
            or normalize_string(
                raw_hit.get(
                    "webformatURL"
                )
            )
        )

        if not download_url:
            return None

        width = parse_int(
            raw_hit.get(
                "imageWidth"
            )
        )

        height = parse_int(
            raw_hit.get(
                "imageHeight"
            )
        )

        if width <= 0:
            width = parse_int(
                raw_hit.get(
                    "webformatWidth"
                )
            )

        if height <= 0:
            height = parse_int(
                raw_hit.get(
                    "webformatHeight"
                )
            )

        tags = normalize_string(
            raw_hit.get("tags")
        )

        image_type = normalize_string(
            raw_hit.get("type")
        )

        title_parts = [
            value
            for value in (
                tags,
                image_type,
            )
            if value
        ]

        title = (
            " | ".join(
                title_parts
            )
            or f"Pixabay image {media_id}"
        )

        username = normalize_string(
            raw_hit.get("user")
        )

        user_id = parse_int(
            raw_hit.get("user_id")
        )

        author_url = build_author_url(
            username=username,
            user_id=user_id,
        )

        thumbnail_url = (
            normalize_string(
                raw_hit.get(
                    "previewURL"
                )
            )
            or normalize_string(
                raw_hit.get(
                    "webformatURL"
                )
            )
        )

        file_size = parse_int(
            raw_hit.get(
                "imageSize"
            )
        )

        score = (
            self._calculate_initial_score(
                raw_hit=raw_hit,
                width=width,
                height=height,
            )
        )

        return MediaCandidate(
            provider=self.name,
            media_id=str(media_id),
            media_kind="image",
            title=title,
            source_url=source_url,
            download_url=download_url,
            width=max(
                0,
                width,
            ),
            height=max(
                0,
                height,
            ),
            author=username,
            author_url=author_url,
            license_name=(
                PIXABAY_LICENSE_NAME
            ),
            license_url=(
                PIXABAY_LICENSE_URL
            ),
            thumbnail_url=(
                thumbnail_url
            ),
            duration_seconds=None,
            file_extension=(
                infer_extension(
                    download_url
                )
            ),
            file_size_bytes=(
                file_size
                if file_size > 0
                else None
            ),
            score=score,
        )

    @staticmethod
    def _calculate_initial_score(
        *,
        raw_hit: dict[str, Any],
        width: int,
        height: int,
    ) -> float:
        score = 0.0

        pixel_count = (
            width * height
        )

        if pixel_count >= 12_000_000:
            score += 30.0
        elif pixel_count >= 8_000_000:
            score += 26.0
        elif pixel_count >= 4_000_000:
            score += 22.0
        elif pixel_count >= 2_000_000:
            score += 16.0
        elif pixel_count > 0:
            score += 8.0

        if height > width:
            score += 20.0
        elif height == width:
            score += 12.0
        else:
            score += 6.0

        likes = parse_int(
            raw_hit.get("likes")
        )

        downloads = parse_int(
            raw_hit.get(
                "downloads"
            )
        )

        views = parse_int(
            raw_hit.get("views")
        )

        score += min(
            15.0,
            likes / 100,
        )

        score += min(
            10.0,
            downloads / 10_000,
        )

        score += min(
            5.0,
            views / 100_000,
        )

        return round(
            score,
            3,
        )


def build_argument_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Pixabay?먯꽌 ?대?吏瑜?"
            "寃?됲븯怨??ㅼ슫濡쒕뱶?⑸땲??"
        )
    )

    parser.add_argument(
        "--query",
        default="underground city",
    )

    parser.add_argument(
        "--orientation",
        choices=[
            "portrait",
            "landscape",
            "square",
            "any",
        ],
        default="any",
    )

    parser.add_argument(
        "--max-results",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--min-width",
        type=int,
        default=720,
    )

    parser.add_argument(
        "--min-height",
        type=int,
        default=720,
    )

    parser.add_argument(
        "--download",
        action="store_true",
    )

    parser.add_argument(
        "--output",
        default=(
            "projects/episodes/ep008/"
            "assets/pixabay_test.jpg"
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    return parser


def print_candidates(
    candidates: list[
        MediaCandidate
    ],
) -> None:
    print("=" * 72)
    print(
        " YouTube Content Factory "
        "Pixabay Provider"
    )
    print("=" * 72)

    if not candidates:
        print(
            "[NO RESULT] No matching images."
        )
        return

    for index, candidate in enumerate(
        candidates,
        start=1,
    ):
        print(
            f"[{index:02d}] "
            f"{candidate.title}"
        )

        print(
            f"     size: "
            f"{candidate.width}x"
            f"{candidate.height}"
        )

        print(
            f"     orientation: "
            f"{candidate.orientation}"
        )

        print(
            f"     score: "
            f"{candidate.score:.3f}"
        )

        print(
            f"     author: "
            f"{candidate.author or 'unknown'}"
        )

        print(
            f"     source: "
            f"{candidate.source_url}"
        )

    print("-" * 72)

    print(
        f"[OK] {len(candidates)} "
        "Pixabay candidates"
    )


def main(
) -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    try:
        request = MediaSearchRequest(
            query=arguments.query,
            media_kind="image",
            orientation=(
                arguments.orientation
            ),
            max_results=(
                arguments.max_results
            ),
            min_width=(
                arguments.min_width
            ),
            min_height=(
                arguments.min_height
            ),
            safe_search=True,
        )

        with PixabayProvider() as provider:
            candidates = (
                provider.search(
                    request
                )
            )

            print_candidates(
                candidates
            )

            if arguments.download:
                if not candidates:
                    raise PixabayProviderError(
                        "No candidate to download."
                    )

                selected = candidates[0]

                output_path = Path(
                    arguments.output
                )

                extension = (
                    selected.file_extension
                )

                if extension:
                    output_path = (
                        output_path.with_suffix(
                            f".{extension}"
                        )
                    )

                result = provider.download(
                    candidate=selected,
                    output_path=output_path,
                    overwrite=(
                        arguments.overwrite
                    ),
                )

                print("-" * 72)
                print("[DOWNLOAD COMPLETE]")
                print(
                    f"file: {result.output_path}"
                )
                print(
                    "size: "
                    f"{result.file_size_bytes:,} bytes"
                )
                print(
                    f"source: "
                    f"{selected.source_url}"
                )

    except (
        PixabayProviderError,
        HttpClientError,
        ValueError,
        OSError,
    ) as exc:
        print(
            f"[FAILED] {exc}",
            file=sys.stderr,
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
