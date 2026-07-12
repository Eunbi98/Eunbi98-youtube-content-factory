from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


MediaKind = Literal[
    "image",
    "video",
]


Orientation = Literal[
    "portrait",
    "landscape",
    "square",
    "any",
]


class MediaProviderError(RuntimeError):
    """미디어 Provider 실행 중 발생한 오류입니다."""


@dataclass(
    frozen=True,
    slots=True,
)
class MediaSearchRequest:
    query: str
    media_kind: MediaKind = "image"
    orientation: Orientation = "portrait"
    max_results: int = 10
    min_width: int = 720
    min_height: int = 1280
    safe_search: bool = True

    def __post_init__(
        self,
    ) -> None:
        normalized_query = (
            self.query
            .strip()
        )

        if not normalized_query:
            raise ValueError(
                "미디어 검색어는 비어 있을 수 없습니다."
            )

        object.__setattr__(
            self,
            "query",
            normalized_query,
        )

        if self.media_kind not in {
            "image",
            "video",
        }:
            raise ValueError(
                "지원하지 않는 media_kind입니다: "
                f"{self.media_kind}"
            )

        if self.orientation not in {
            "portrait",
            "landscape",
            "square",
            "any",
        }:
            raise ValueError(
                "지원하지 않는 orientation입니다: "
                f"{self.orientation}"
            )

        if self.max_results <= 0:
            raise ValueError(
                "max_results는 1 이상이어야 합니다."
            )

        if self.max_results > 100:
            raise ValueError(
                "max_results는 100 이하여야 합니다."
            )

        if self.min_width <= 0:
            raise ValueError(
                "min_width는 1 이상이어야 합니다."
            )

        if self.min_height <= 0:
            raise ValueError(
                "min_height는 1 이상이어야 합니다."
            )


@dataclass(
    frozen=True,
    slots=True,
)
class MediaCandidate:
    provider: str
    media_id: str
    media_kind: MediaKind

    title: str
    source_url: str
    download_url: str

    width: int
    height: int

    author: str | None = None
    author_url: str | None = None
    license_name: str | None = None
    license_url: str | None = None

    thumbnail_url: str | None = None
    duration_seconds: float | None = None

    file_extension: str | None = None
    file_size_bytes: int | None = None

    score: float = 0.0

    def __post_init__(
        self,
    ) -> None:
        normalized_provider = (
            self.provider
            .strip()
            .lower()
        )

        normalized_media_id = (
            self.media_id
            .strip()
        )

        normalized_title = (
            self.title
            .strip()
        )

        normalized_source_url = (
            self.source_url
            .strip()
        )

        normalized_download_url = (
            self.download_url
            .strip()
        )

        if not normalized_provider:
            raise ValueError(
                "provider는 비어 있을 수 없습니다."
            )

        if not normalized_media_id:
            raise ValueError(
                "media_id는 비어 있을 수 없습니다."
            )

        if self.media_kind not in {
            "image",
            "video",
        }:
            raise ValueError(
                "지원하지 않는 media_kind입니다: "
                f"{self.media_kind}"
            )

        if not normalized_title:
            normalized_title = (
                normalized_media_id
            )

        if not normalized_source_url:
            raise ValueError(
                "source_url은 비어 있을 수 없습니다."
            )

        if not normalized_download_url:
            raise ValueError(
                "download_url은 비어 있을 수 없습니다."
            )

        if self.width < 0:
            raise ValueError(
                "width는 0 이상이어야 합니다."
            )

        if self.height < 0:
            raise ValueError(
                "height는 0 이상이어야 합니다."
            )

        if (
            self.duration_seconds is not None
            and self.duration_seconds < 0
        ):
            raise ValueError(
                "duration_seconds는 "
                "0 이상이어야 합니다."
            )

        if (
            self.file_size_bytes is not None
            and self.file_size_bytes < 0
        ):
            raise ValueError(
                "file_size_bytes는 "
                "0 이상이어야 합니다."
            )

        object.__setattr__(
            self,
            "provider",
            normalized_provider,
        )

        object.__setattr__(
            self,
            "media_id",
            normalized_media_id,
        )

        object.__setattr__(
            self,
            "title",
            normalized_title,
        )

        object.__setattr__(
            self,
            "source_url",
            normalized_source_url,
        )

        object.__setattr__(
            self,
            "download_url",
            normalized_download_url,
        )

        if self.file_extension:
            normalized_extension = (
                self.file_extension
                .strip()
                .lower()
                .lstrip(".")
            )

            object.__setattr__(
                self,
                "file_extension",
                normalized_extension
                or None,
            )

    @property
    def aspect_ratio(
        self,
    ) -> float | None:
        if (
            self.width <= 0
            or self.height <= 0
        ):
            return None

        return round(
            self.width
            / self.height,
            4,
        )

    @property
    def orientation(
        self,
    ) -> Orientation:
        if (
            self.width <= 0
            or self.height <= 0
        ):
            return "any"

        if self.width == self.height:
            return "square"

        if self.width > self.height:
            return "landscape"

        return "portrait"

    def matches_request(
        self,
        request: MediaSearchRequest,
    ) -> bool:
        if (
            self.media_kind
            != request.media_kind
        ):
            return False

        if (
            self.width > 0
            and self.width
            < request.min_width
        ):
            return False

        if (
            self.height > 0
            and self.height
            < request.min_height
        ):
            return False

        if (
            request.orientation
            != "any"
            and self.orientation
            != request.orientation
        ):
            return False

        return True

    def with_score(
        self,
        score: float,
    ) -> "MediaCandidate":
        return MediaCandidate(
            provider=self.provider,
            media_id=self.media_id,
            media_kind=self.media_kind,
            title=self.title,
            source_url=self.source_url,
            download_url=self.download_url,
            width=self.width,
            height=self.height,
            author=self.author,
            author_url=self.author_url,
            license_name=self.license_name,
            license_url=self.license_url,
            thumbnail_url=self.thumbnail_url,
            duration_seconds=(
                self.duration_seconds
            ),
            file_extension=(
                self.file_extension
            ),
            file_size_bytes=(
                self.file_size_bytes
            ),
            score=round(
                float(score),
                3,
            ),
        )

    def build_filename(
        self,
        *,
        scene_id: str,
        fallback_extension: str,
    ) -> str:
        normalized_scene_id = (
            scene_id
            .strip()
        )

        if not normalized_scene_id:
            raise ValueError(
                "scene_id는 비어 있을 수 없습니다."
            )

        extension = (
            self.file_extension
            or fallback_extension
        )

        normalized_extension = (
            extension
            .strip()
            .lower()
            .lstrip(".")
        )

        if not normalized_extension:
            raise ValueError(
                "파일 확장자가 비어 있습니다."
            )

        return (
            f"{normalized_scene_id}."
            f"{normalized_extension}"
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "provider": self.provider,
            "mediaId": self.media_id,
            "mediaKind": self.media_kind,
            "title": self.title,
            "sourceUrl": self.source_url,
            "downloadUrl": self.download_url,
            "thumbnailUrl": self.thumbnail_url,
            "width": self.width,
            "height": self.height,
            "aspectRatio": self.aspect_ratio,
            "orientation": self.orientation,
            "durationSeconds": (
                self.duration_seconds
            ),
            "author": self.author,
            "authorUrl": self.author_url,
            "licenseName": (
                self.license_name
            ),
            "licenseUrl": (
                self.license_url
            ),
            "fileExtension": (
                self.file_extension
            ),
            "fileSizeBytes": (
                self.file_size_bytes
            ),
            "score": self.score,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class MediaDownloadResult:
    candidate: MediaCandidate
    output_path: Path
    file_size_bytes: int

    def __post_init__(
        self,
    ) -> None:
        if self.file_size_bytes <= 0:
            raise ValueError(
                "다운로드 파일 크기는 "
                "0보다 커야 합니다."
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "candidate": (
                self.candidate.to_dict()
            ),
            "outputPath": str(
                self.output_path
            ),
            "fileSizeBytes": (
                self.file_size_bytes
            ),
        }


class MediaProvider(ABC):
    """
    모든 미디어 검색 Provider가 구현해야 하는
    공통 인터페이스입니다.
    """

    @property
    @abstractmethod
    def name(
        self,
    ) -> str:
        """Provider 식별자입니다."""

    @property
    def supported_media_kinds(
        self,
    ) -> frozenset[MediaKind]:
        return frozenset({
            "image",
        })

    def supports(
        self,
        media_kind: MediaKind,
    ) -> bool:
        return (
            media_kind
            in self.supported_media_kinds
        )

    @abstractmethod
    def search(
        self,
        request: MediaSearchRequest,
    ) -> list[MediaCandidate]:
        """
        검색 조건에 맞는 미디어 후보를 반환합니다.
        """

    @abstractmethod
    def download(
        self,
        *,
        candidate: MediaCandidate,
        output_path: Path,
        overwrite: bool = False,
    ) -> MediaDownloadResult:
        """
        선택된 미디어 후보를 로컬 파일로 저장합니다.
        """

    def validate_request(
        self,
        request: MediaSearchRequest,
    ) -> None:
        if not self.supports(
            request.media_kind
        ):
            raise MediaProviderError(
                f"{self.name} Provider는 "
                f"{request.media_kind} 검색을 "
                "지원하지 않습니다."
            )

    def filter_candidates(
        self,
        *,
        request: MediaSearchRequest,
        candidates: list[MediaCandidate],
    ) -> list[MediaCandidate]:
        filtered = [
            candidate
            for candidate in candidates
            if candidate.matches_request(
                request
            )
        ]

        return filtered[
            : request.max_results
        ]