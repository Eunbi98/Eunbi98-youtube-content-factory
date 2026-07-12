from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Final
from urllib.parse import quote

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


WIKIMEDIA_API_URL: Final[str] = (
    "https://commons.wikimedia.org/w/api.php"
)

WIKIMEDIA_FILE_PAGE_BASE_URL: Final[str] = (
    "https://commons.wikimedia.org/wiki/"
)

DEFAULT_SEARCH_LANGUAGE: Final[str] = "en"
DEFAULT_THUMBNAIL_WIDTH: Final[int] = 1080

SUPPORTED_IMAGE_MIME_TYPES: Final[frozenset[str]] = (
    frozenset(
        {
            "image/jpeg",
            "image/png",
            "image/webp",
            "image/gif",
            "image/tiff",
            "image/svg+xml",
        }
    )
)

MIME_EXTENSION_MAP: Final[dict[str, str]] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/gif": "gif",
    "image/tiff": "tif",
    "image/svg+xml": "svg",
}


class WikimediaProviderError(MediaProviderError):
    """Wikimedia Commons 검색 또는 다운로드 오류입니다."""


def strip_html(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = html.unescape(value)

    normalized = re.sub(
        r"<br\s*/?>",
        " ",
        normalized,
        flags=re.IGNORECASE,
    )

    normalized = re.sub(
        r"<[^>]+>",
        "",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    ).strip()

    return normalized or None


def read_metadata_value(
    metadata: dict[str, Any],
    key: str,
) -> str | None:
    raw_item = metadata.get(key)

    if not isinstance(raw_item, dict):
        return None

    raw_value = raw_item.get("value")

    if not isinstance(raw_value, str):
        return None

    return strip_html(raw_value)


def normalize_file_title(
    title: str,
) -> str:
    normalized = title.strip()

    if normalized.lower().startswith(
        "file:"
    ):
        normalized = normalized[5:]

    return normalized.strip()


def build_file_page_url(
    title: str,
) -> str:
    normalized_title = title.strip()

    if not normalized_title.lower().startswith(
        "file:"
    ):
        normalized_title = (
            f"File:{normalized_title}"
        )

    encoded_title = quote(
        normalized_title.replace(
            " ",
            "_",
        ),
        safe=":",
    )

    return (
        f"{WIKIMEDIA_FILE_PAGE_BASE_URL}"
        f"{encoded_title}"
    )


def infer_extension(
    *,
    mime_type: str | None,
    source_url: str,
) -> str | None:
    if mime_type:
        normalized_mime = (
            mime_type
            .split(";")[0]
            .strip()
            .lower()
        )

        mapped_extension = (
            MIME_EXTENSION_MAP.get(
                normalized_mime
            )
        )

        if mapped_extension:
            return mapped_extension

    url_path = source_url.split(
        "?",
        maxsplit=1,
    )[0]

    suffix = Path(url_path).suffix

    if not suffix:
        return None

    return (
        suffix
        .lower()
        .lstrip(".")
        or None
    )


def parse_page_id(
    raw_page: dict[str, Any],
) -> str:
    raw_page_id = raw_page.get(
        "pageid"
    )

    if isinstance(
        raw_page_id,
        int,
    ):
        return str(raw_page_id)

    raw_title = raw_page.get(
        "title"
    )

    if isinstance(
        raw_title,
        str,
    ):
        return raw_title.strip()

    raise WikimediaProviderError(
        "Wikimedia 검색 결과에서 "
        "media_id를 확인할 수 없습니다."
    )


def parse_dimensions(
    image_info: dict[str, Any],
) -> tuple[int, int]:
    raw_width = image_info.get(
        "width",
        0,
    )

    raw_height = image_info.get(
        "height",
        0,
    )

    width = (
        raw_width
        if isinstance(raw_width, int)
        else 0
    )

    height = (
        raw_height
        if isinstance(raw_height, int)
        else 0
    )

    return (
        max(0, width),
        max(0, height),
    )


class WikimediaProvider(MediaProvider):
    """
    Wikimedia Commons 공식 API 기반 이미지 Provider입니다.

    검색과 이미지 메타데이터 조회를 한 번의
    generator=search 요청으로 처리합니다.
    """

    def __init__(
        self,
        *,
        http_client: HttpClient | None = None,
        language: str = DEFAULT_SEARCH_LANGUAGE,
        thumbnail_width: int = DEFAULT_THUMBNAIL_WIDTH,
    ) -> None:
        normalized_language = (
            language
            .strip()
            .lower()
        )

        if not normalized_language:
            raise ValueError(
                "language는 비어 있을 수 없습니다."
            )

        if thumbnail_width <= 0:
            raise ValueError(
                "thumbnail_width는 "
                "1 이상이어야 합니다."
            )

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

        self._language = (
            normalized_language
        )

        self._thumbnail_width = (
            thumbnail_width
        )

    @property
    def name(
        self,
    ) -> str:
        return "wikimedia"

    @property
    def supported_media_kinds(
        self,
    ) -> frozenset[MediaKind]:
        return frozenset(
            {
                "image",
            }
        )

    def close(
        self,
    ) -> None:
        if self._owns_http_client:
            self._http_client.close()

    def __enter__(
        self,
    ) -> "WikimediaProvider":
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

        api_result_limit = min(
            50,
            max(
                request.max_results * 4,
                request.max_results,
            ),
        )

        params: dict[str, object] = {
            "action": "query",
            "format": "json",
            "formatversion": "2",

            # 파일 네임스페이스만 검색합니다.
            "generator": "search",
            "gsrsearch": request.query,
            "gsrnamespace": 6,
            "gsrlimit": api_result_limit,

            # 원본 URL, 크기, MIME, 라이선스 메타데이터
            "prop": "imageinfo",
            "iiprop": (
                "url|size|mime|extmetadata"
            ),

            # 프리뷰·후보 검사용 썸네일
            "iiurlwidth": (
                self._thumbnail_width
            ),

            "uselang": self._language,
        }

        try:
            payload = (
                self._http_client.get_json(
                    WIKIMEDIA_API_URL,
                    params=params,
                )
            )

        except (
            HttpClientError,
            ValueError,
        ) as exc:
            raise WikimediaProviderError(
                "Wikimedia Commons 검색에 "
                "실패했습니다.\n"
                f"검색어: {request.query}\n"
                f"원인: {exc}"
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
        if candidate.provider != self.name:
            raise WikimediaProviderError(
                "다른 Provider의 후보는 "
                "WikimediaProvider로 "
                "다운로드할 수 없습니다.\n"
                f"candidate.provider: "
                f"{candidate.provider}"
            )

        if candidate.media_kind != "image":
            raise WikimediaProviderError(
                "WikimediaProvider는 현재 "
                "이미지 다운로드만 지원합니다."
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
            raise WikimediaProviderError(
                "Wikimedia 이미지 다운로드에 "
                "실패했습니다.\n"
                f"제목: {candidate.title}\n"
                f"URL: "
                f"{candidate.download_url}\n"
                f"원인: {exc}"
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
        raw_query = payload.get(
            "query"
        )

        if not isinstance(
            raw_query,
            dict,
        ):
            return []

        raw_pages = raw_query.get(
            "pages"
        )

        if not isinstance(
            raw_pages,
            list,
        ):
            return []

        candidates: list[
            MediaCandidate
        ] = []

        for raw_page in raw_pages:
            if not isinstance(
                raw_page,
                dict,
            ):
                continue

            candidate = (
                self._parse_page_candidate(
                    raw_page
                )
            )

            if candidate is not None:
                candidates.append(
                    candidate
                )

        return candidates

    def _parse_page_candidate(
        self,
        raw_page: dict[str, Any],
    ) -> MediaCandidate | None:
        raw_title = raw_page.get(
            "title"
        )

        if not isinstance(
            raw_title,
            str,
        ):
            return None

        raw_image_info_list = (
            raw_page.get(
                "imageinfo"
            )
        )

        if not isinstance(
            raw_image_info_list,
            list,
        ):
            return None

        if not raw_image_info_list:
            return None

        raw_image_info = (
            raw_image_info_list[0]
        )

        if not isinstance(
            raw_image_info,
            dict,
        ):
            return None

        raw_download_url = (
            raw_image_info.get(
                "url"
            )
        )

        if not isinstance(
            raw_download_url,
            str,
        ):
            return None

        download_url = (
            raw_download_url.strip()
        )

        if not download_url:
            return None

        raw_mime_type = (
            raw_image_info.get(
                "mime"
            )
        )

        mime_type = (
            raw_mime_type
            .strip()
            .lower()
            if isinstance(
                raw_mime_type,
                str,
            )
            else None
        )

        if (
            mime_type is not None
            and mime_type
            not in SUPPORTED_IMAGE_MIME_TYPES
        ):
            return None

        width, height = (
            parse_dimensions(
                raw_image_info
            )
        )

        raw_metadata = (
            raw_image_info.get(
                "extmetadata"
            )
        )

        metadata = (
            raw_metadata
            if isinstance(
                raw_metadata,
                dict,
            )
            else {}
        )

        description = (
            read_metadata_value(
                metadata,
                "ImageDescription",
            )
        )

        object_name = (
            read_metadata_value(
                metadata,
                "ObjectName",
            )
        )

        artist = read_metadata_value(
            metadata,
            "Artist",
        )

        credit = read_metadata_value(
            metadata,
            "Credit",
        )

        license_name = (
            read_metadata_value(
                metadata,
                "LicenseShortName",
            )
        )

        license_url = (
            read_metadata_value(
                metadata,
                "LicenseUrl",
            )
        )

        attribution_required = (
            read_metadata_value(
                metadata,
                "AttributionRequired",
            )
        )

        raw_thumb_url = (
            raw_image_info.get(
                "thumburl"
            )
        )

        thumbnail_url = (
            raw_thumb_url.strip()
            if isinstance(
                raw_thumb_url,
                str,
            )
            else None
        )

        title = (
            object_name
            or description
            or normalize_file_title(
                raw_title
            )
        )

        author = (
            artist
            or credit
        )

        file_extension = (
            infer_extension(
                mime_type=mime_type,
                source_url=download_url,
            )
        )

        media_id = parse_page_id(
            raw_page
        )

        source_url = (
            build_file_page_url(
                raw_title
            )
        )

        score = (
            self._calculate_initial_score(
                width=width,
                height=height,
                license_name=(
                    license_name
                ),
                attribution_required=(
                    attribution_required
                ),
            )
        )

        return MediaCandidate(
            provider=self.name,
            media_id=media_id,
            media_kind="image",
            title=title,
            source_url=source_url,
            download_url=download_url,
            width=width,
            height=height,
            author=author,
            author_url=None,
            license_name=license_name,
            license_url=license_url,
            thumbnail_url=thumbnail_url,
            duration_seconds=None,
            file_extension=(
                file_extension
            ),
            file_size_bytes=None,
            score=score,
        )

    @staticmethod
    def _calculate_initial_score(
        *,
        width: int,
        height: int,
        license_name: str | None,
        attribution_required: str | None,
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

        if license_name:
            score += 10.0

        if attribution_required:
            normalized = (
                attribution_required
                .strip()
                .lower()
            )

            if normalized in {
                "false",
                "no",
                "0",
            }:
                score += 5.0

        return round(
            score,
            3,
        )


def build_argument_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Wikimedia Commons에서 "
            "이미지를 검색하고 다운로드합니다."
        )
    )

    parser.add_argument(
        "--query",
        default="Pompeii ruins",
        help="Wikimedia 이미지 검색어",
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
        default=10,
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
        help=(
            "검색 결과 1위를 실제로 "
            "다운로드합니다."
        ),
    )

    parser.add_argument(
        "--output",
        default=(
            "projects/episodes/ep008/"
            "assets/scene_001.jpg"
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    parser.add_argument(
        "--json-output",
        default=None,
        help=(
            "검색 결과 JSON 저장 경로"
        ),
    )

    return parser


def print_candidates(
    candidates: list[MediaCandidate],
) -> None:
    print("=" * 72)
    print(
        " YouTube Content Factory "
        "Wikimedia Provider"
    )
    print("=" * 72)

    if not candidates:
        print(
            "[결과 없음] 조건에 맞는 "
            "이미지를 찾지 못했습니다."
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
            f"     크기: "
            f"{candidate.width}x"
            f"{candidate.height}"
        )

        print(
            f"     방향: "
            f"{candidate.orientation}"
        )

        print(
            f"     점수: "
            f"{candidate.score:.3f}"
        )

        print(
            f"     작가: "
            f"{candidate.author or '미상'}"
        )

        print(
            f"     라이선스: "
            f"{candidate.license_name or '미확인'}"
        )

        print(
            f"     출처: "
            f"{candidate.source_url}"
        )

    print("-" * 72)
    print(
        f"[성공] Wikimedia 후보 "
        f"{len(candidates)}개 검색 완료"
    )


def save_candidates_json(
    *,
    candidates: list[MediaCandidate],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            {
                "provider": "wikimedia",
                "candidateCount": len(
                    candidates
                ),
                "candidates": [
                    candidate.to_dict()
                    for candidate
                    in candidates
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
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

        with WikimediaProvider() as provider:
            candidates = provider.search(
                request
            )

            print_candidates(
                candidates
            )

            if arguments.json_output:
                save_candidates_json(
                    candidates=candidates,
                    output_path=Path(
                        arguments.json_output
                    ),
                )

            if arguments.download:
                if not candidates:
                    raise WikimediaProviderError(
                        "다운로드할 후보가 없습니다."
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

                print(
                    "[다운로드 완료]"
                )

                print(
                    f"파일: "
                    f"{result.output_path}"
                )

                print(
                    f"크기: "
                    f"{result.file_size_bytes:,} "
                    "bytes"
                )

                print(
                    f"출처: "
                    f"{selected.source_url}"
                )

                print(
                    f"라이선스: "
                    f"{selected.license_name or '미확인'}"
                )

    except (
        WikimediaProviderError,
        HttpClientError,
        ValueError,
        OSError,
    ) as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )

        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )