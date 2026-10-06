from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from base_provider import (
    MediaCandidate,
    MediaKind,
    MediaProvider,
    MediaProviderError,
    MediaSearchRequest,
)


class ProviderRegistryError(RuntimeError):
    """Provider Registry 실행 중 발생한 오류입니다."""


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderSearchFailure:
    provider: str
    message: str

    def to_dict(
        self,
    ) -> dict[str, str]:
        return {
            "provider": self.provider,
            "message": self.message,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class ProviderSearchResult:
    request: MediaSearchRequest
    candidates: tuple[
        MediaCandidate,
        ...,
    ]
    failures: tuple[
        ProviderSearchFailure,
        ...,
    ]
    searched_provider_count: int

    @property
    def succeeded_provider_count(
        self,
    ) -> int:
        return (
            self.searched_provider_count
            - len(self.failures)
        )

    @property
    def candidate_count(
        self,
    ) -> int:
        return len(
            self.candidates
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "request": {
                "query": self.request.query,
                "mediaKind": (
                    self.request.media_kind
                ),
                "orientation": (
                    self.request.orientation
                ),
                "maxResults": (
                    self.request.max_results
                ),
                "minWidth": (
                    self.request.min_width
                ),
                "minHeight": (
                    self.request.min_height
                ),
                "safeSearch": (
                    self.request.safe_search
                ),
            },
            "searchedProviderCount": (
                self.searched_provider_count
            ),
            "succeededProviderCount": (
                self.succeeded_provider_count
            ),
            "candidateCount": (
                self.candidate_count
            ),
            "failures": [
                failure.to_dict()
                for failure in self.failures
            ],
            "candidates": [
                candidate.to_dict()
                for candidate
                in self.candidates
            ],
        }


class MediaProviderRegistry:
    """
    Media Provider 등록·조회·통합 검색 관리자입니다.

    개별 Provider의 오류가 전체 검색을 중단시키지 않도록
    Provider별 실패를 수집하고 나머지 검색은 계속합니다.
    """

    def __init__(
        self,
        providers: Iterable[
            MediaProvider
        ] | None = None,
    ) -> None:
        self._providers: dict[
            str,
            MediaProvider,
        ] = {}

        if providers:
            for provider in providers:
                self.register(
                    provider
                )

    def register(
        self,
        provider: MediaProvider,
        *,
        replace: bool = False,
    ) -> None:
        provider_name = (
            self._normalize_provider_name(
                provider.name
            )
        )

        if (
            provider_name
            in self._providers
            and not replace
        ):
            raise ProviderRegistryError(
                "이미 등록된 Provider입니다: "
                f"{provider_name}"
            )

        self._providers[
            provider_name
        ] = provider

    def unregister(
        self,
        provider_name: str,
    ) -> MediaProvider:
        normalized_name = (
            self._normalize_provider_name(
                provider_name
            )
        )

        provider = self._providers.pop(
            normalized_name,
            None,
        )

        if provider is None:
            raise ProviderRegistryError(
                "등록되지 않은 Provider입니다: "
                f"{normalized_name}"
            )

        return provider

    def clear(
        self,
    ) -> None:
        self._providers.clear()

    def get(
        self,
        provider_name: str,
    ) -> MediaProvider:
        normalized_name = (
            self._normalize_provider_name(
                provider_name
            )
        )

        provider = self._providers.get(
            normalized_name
        )

        if provider is None:
            raise ProviderRegistryError(
                "등록되지 않은 Provider입니다: "
                f"{normalized_name}"
            )

        return provider

    def contains(
        self,
        provider_name: str,
    ) -> bool:
        normalized_name = (
            self._normalize_provider_name(
                provider_name
            )
        )

        return (
            normalized_name
            in self._providers
        )

    def list_provider_names(
        self,
        *,
        media_kind: MediaKind | None = None,
    ) -> tuple[str, ...]:
        names: list[str] = []

        for name, provider in sorted(
            self._providers.items(),
            key=lambda item: item[0],
        ):
            if (
                media_kind is not None
                and not provider.supports(
                    media_kind
                )
            ):
                continue

            names.append(name)

        return tuple(names)

    def list_providers(
        self,
        *,
        media_kind: MediaKind | None = None,
    ) -> tuple[
        MediaProvider,
        ...,
    ]:
        names = self.list_provider_names(
            media_kind=media_kind
        )

        return tuple(
            self._providers[name]
            for name in names
        )

    def search(
        self,
        request: MediaSearchRequest,
        *,
        provider_names: Iterable[
            str
        ] | None = None,
        continue_on_error: bool = True,
        deduplicate: bool = True,
    ) -> ProviderSearchResult:
        providers = (
            self._resolve_search_providers(
                request=request,
                provider_names=(
                    provider_names
                ),
            )
        )

        if not providers:
            raise ProviderRegistryError(
                "검색 가능한 Provider가 없습니다.\n"
                f"media_kind: "
                f"{request.media_kind}"
            )

        candidates: list[
            MediaCandidate
        ] = []

        failures: list[
            ProviderSearchFailure
        ] = []

        for provider in providers:
            try:
                provider.validate_request(
                    request
                )

                provider_candidates = (
                    provider.search(
                        request
                    )
                )

                filtered_candidates = (
                    provider.filter_candidates(
                        request=request,
                        candidates=(
                            provider_candidates
                        ),
                    )
                )

                candidates.extend(
                    filtered_candidates
                )

            except (
                MediaProviderError,
                ValueError,
                OSError,
                RuntimeError,
            ) as exc:
                failure = (
                    ProviderSearchFailure(
                        provider=(
                            provider.name
                        ),
                        message=str(exc),
                    )
                )

                failures.append(
                    failure
                )

                if not continue_on_error:
                    raise ProviderRegistryError(
                        "Provider 검색에 "
                        "실패했습니다.\n"
                        f"provider: "
                        f"{provider.name}\n"
                        f"원인: {exc}"
                    ) from exc

        if deduplicate:
            candidates = (
                self._deduplicate_candidates(
                    candidates
                )
            )

        candidates = self._sort_candidates(
            candidates
        )

        return ProviderSearchResult(
            request=request,
            candidates=tuple(
                candidates
            ),
            failures=tuple(
                failures
            ),
            searched_provider_count=len(
                providers
            ),
        )

    def _resolve_search_providers(
        self,
        *,
        request: MediaSearchRequest,
        provider_names: Iterable[
            str
        ] | None,
    ) -> list[
        MediaProvider
    ]:
        if provider_names is None:
            return list(
                self.list_providers(
                    media_kind=(
                        request.media_kind
                    )
                )
            )

        resolved: list[
            MediaProvider
        ] = []

        seen_names: set[str] = set()

        for raw_name in provider_names:
            normalized_name = (
                self._normalize_provider_name(
                    raw_name
                )
            )

            if normalized_name in seen_names:
                continue

            seen_names.add(
                normalized_name
            )

            provider = self.get(
                normalized_name
            )

            if not provider.supports(
                request.media_kind
            ):
                continue

            resolved.append(
                provider
            )

        return resolved

    @staticmethod
    def _deduplicate_candidates(
        candidates: list[
            MediaCandidate
        ],
    ) -> list[
        MediaCandidate
    ]:
        deduplicated: list[
            MediaCandidate
        ] = []

        seen_keys: set[
            tuple[str, str]
        ] = set()

        seen_download_urls: set[str] = set()

        for candidate in candidates:
            identity_key = (
                candidate.provider,
                candidate.media_id,
            )

            if identity_key in seen_keys:
                continue

            if (
                candidate.download_url
                in seen_download_urls
            ):
                continue

            seen_keys.add(
                identity_key
            )

            seen_download_urls.add(
                candidate.download_url
            )

            deduplicated.append(
                candidate
            )

        return deduplicated

    @staticmethod
    def _sort_candidates(
        candidates: list[
            MediaCandidate
        ],
    ) -> list[
        MediaCandidate
    ]:
        return sorted(
            candidates,
            key=lambda candidate: (
                -candidate.score,
                -(
                    candidate.width
                    * candidate.height
                ),
                candidate.provider,
                candidate.media_id,
            ),
        )

    @staticmethod
    def _normalize_provider_name(
        provider_name: str,
    ) -> str:
        normalized_name = (
            provider_name
            .strip()
            .lower()
        )

        if not normalized_name:
            raise ProviderRegistryError(
                "Provider 이름은 "
                "비어 있을 수 없습니다."
            )

        return normalized_name


def main() -> int:
    """
    실제 Provider 구현 전 Registry 자체 동작을
    검증하기 위한 간단한 테스트입니다.
    """

    registry = (
        MediaProviderRegistry()
    )

    print("=" * 62)
    print(
        " YouTube Content Factory "
        "Media Provider Registry"
    )
    print("=" * 62)
    print(
        f"{'provider_count':>18}: "
        f"{len(registry.list_provider_names())}"
    )
    print(
        f"{'providers':>18}: "
        f"{registry.list_provider_names()}"
    )
    print("-" * 62)
    print(
        "[성공] Provider Registry "
        "초기화 완료"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )