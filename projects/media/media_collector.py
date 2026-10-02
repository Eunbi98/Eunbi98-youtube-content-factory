from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import replace
from pathlib import Path
from typing import Any

MEDIA_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MEDIA_DIR.parents[1]

for module_path in (
    MEDIA_DIR,
    MEDIA_DIR / "providers",
):
    module_path_text = str(
        module_path
    )
    if module_path_text not in sys.path:
        sys.path.insert(
            0,
            module_path_text,
        )

from api_key_loader import load_api_keys  # noqa: E402
from cache_manager import CacheManager  # noqa: E402
from downloader import MediaDownloadError, MediaDownloader  # noqa: E402
from manifest_builder import ManifestBuilder  # noqa: E402
from media_ranker import rerank_candidates  # noqa: E402
from provider_models import MediaCandidate  # noqa: E402
from providers.nasa_provider import NasaProvider  # noqa: E402
from providers.openverse_provider import OpenverseProvider  # noqa: E402
from providers.pixabay_provider import PixabayProvider  # noqa: E402
from providers.wikimedia_provider import WikimediaProvider  # noqa: E402


SPACE_TERMS = {
    "nasa",
    "mars",
    "moon",
    "space",
    "galaxy",
    "asteroid",
    "planet",
    "solar",
    "astronaut",
}

LIFESTYLE_TERMS = {
    "person",
    "people",
    "sleep",
    "sleeping",
    "bed",
    "bedroom",
    "wake",
    "wakes",
    "awake",
    "tired",
    "stress",
    "stressed",
}

GENERIC_SEARCH_TERMS = {
    "a",
    "an",
    "and",
    "close",
    "closeup",
    "concept",
    "detailed",
    "illustration",
    "image",
    "of",
    "photo",
    "photograph",
    "scene",
    "showing",
    "stock",
    "the",
    "view",
    "with",
}


def fallback_queries(
    *queries: str,
) -> list[str]:
    """Build progressively broader English searches without changing topic."""
    fallbacks: list[str] = []

    def add(value: str) -> None:
        normalized = " ".join(value.split()).strip()
        if normalized and normalized.casefold() not in {
            item.casefold() for item in fallbacks
        }:
            fallbacks.append(normalized)

    for query in queries:
        words = [
            word.casefold()
            for word in re.findall(
                r"[A-Za-z][A-Za-z0-9'-]*",
                query,
            )
            if word.casefold() not in GENERIC_SEARCH_TERMS
        ]
        if not words:
            continue

        meaningful = [
            word
            for word in words
            if word not in LIFESTYLE_TERMS
        ] or words

        # Try a focused phrase first, then pairs and single topic terms.
        add(" ".join(meaningful[:3]))
        if len(meaningful) >= 2:
            add(" ".join(meaningful[-2:]))
        for word in reversed(meaningful):
            if len(word) >= 4:
                add(word)

    return fallbacks


class MediaCollectorError(RuntimeError):
    pass


def load_json_object(
    path: Path,
) -> dict[str, Any]:
    try:
        data = json.loads(
            path.read_text(
                encoding="utf-8"
            )
        )
    except (
        OSError,
        json.JSONDecodeError,
    ) as exc:
        raise MediaCollectorError(
            "JSON 파일을 읽지 못했습니다.\n"
            f"파일: {path}\n"
            f"원인: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise MediaCollectorError(
            "JSON 최상위 값은 객체여야 합니다."
        )

    return data


def candidate_from_dict(
    data: dict[str, Any],
) -> MediaCandidate:
    return MediaCandidate(**data)


def candidate_to_dict(
    candidate: MediaCandidate,
) -> dict[str, Any]:
    return candidate.to_dict()


def should_use_nasa(
    query: str,
) -> bool:
    normalized = query.casefold()
    return any(
        term in normalized
        for term in SPACE_TERMS
    )


class MediaCollector:
    def __init__(
        self,
        *,
        episode_id: str,
    ) -> None:
        self.episode_id = episode_id
        self.episode_dir = (
            PROJECT_ROOT
            / "projects"
            / "episodes"
            / episode_id
        )
        self.query_path = (
            self.episode_dir
            / "media_queries.json"
        )
        self.assets_dir = (
            self.episode_dir
            / "assets"
        )
        self.cache = CacheManager(
            PROJECT_ROOT
            / "projects"
            / "output"
            / "media_cache"
        )
        self.api_keys = load_api_keys(
            PROJECT_ROOT
        )
        self.wikimedia = (
            WikimediaProvider()
        )
        self.nasa = NasaProvider()
        self.openverse = OpenverseProvider()

        pixabay_api_key = (
            self.api_keys.get(
                "pixabay",
                "",
            ).strip()
        )
        self.pixabay = (
            PixabayProvider(
                api_key=pixabay_api_key,
            )
            if pixabay_api_key
            else None
        )

        self.downloader = (
            MediaDownloader()
        )

    def collect(
        self,
        *,
        force: bool = False,
        query_limit: int = 5,
        candidates_per_query: int = 20,
    ) -> Path:
        if not self.query_path.exists():
            raise MediaCollectorError(
                "media_queries.json이 없습니다.\n"
                f"파일: {self.query_path}"
            )

        payload = load_json_object(
            self.query_path
        )
        raw_scenes = payload.get(
            "scenes"
        )

        if not isinstance(
            raw_scenes,
            list,
        ):
            raise MediaCollectorError(
                "media_queries.json의 scenes가 "
                "배열이 아닙니다."
            )

        manifest = ManifestBuilder(
            episode_id=self.episode_id,
            episode_dir=self.episode_dir,
        )
        used_media: set[tuple[str, str]] = set()

        for raw_scene in raw_scenes:
            if not isinstance(
                raw_scene,
                dict,
            ):
                continue

            scene_id = str(
                raw_scene.get(
                    "sceneId",
                    "",
                )
            ).strip()

            raw_queries = raw_scene.get(
                "queries"
            )

            if (
                not scene_id
                or not isinstance(
                    raw_queries,
                    list,
                )
            ):
                continue

            existing = list(
                self.assets_dir.glob(
                    f"{scene_id}.*"
                )
            )

            if existing and not force:
                print(
                    f"[SKIP] {scene_id}: "
                    "기존 파일 사용"
                )
                continue

            candidates: list[
                MediaCandidate
            ] = []
            searched_queries: list[str] = []

            for raw_query in (
                raw_queries[:query_limit]
            ):
                if not isinstance(
                    raw_query,
                    dict,
                ):
                    continue

                query = str(
                    raw_query.get(
                        "query",
                        "",
                    )
                ).strip()

                if not query:
                    continue

                searched_queries.append(query)
                normalized_query_terms = {
                    term.casefold()
                    for term in query.split()
                }

                is_lifestyle_query = bool(
                    normalized_query_terms
                    & LIFESTYLE_TERMS
                )

                candidates.extend(
                    self._search_provider(
                        provider_name="openverse",
                        query=query,
                        limit=candidates_per_query,
                    )
                )

                if should_use_nasa(query):
                    candidates.extend(
                        self._search_provider(
                            provider_name="nasa",
                            query=query,
                            limit=min(
                                candidates_per_query,
                                10,
                            ),
                        )
                    )

                if not is_lifestyle_query:
                    candidates.extend(
                        self._search_provider(
                            provider_name="wikimedia",
                            query=query,
                            limit=candidates_per_query,
                        )
                    )

                if self.pixabay is not None:
                    candidates.extend(
                        self._search_provider(
                            provider_name="pixabay",
                            query=query,
                            limit=candidates_per_query,
                        )
                    )

            primary_query = str(
                raw_scene.get(
                    "primaryQuery",
                    "",
                )
            ).strip()

            if not candidates:
                original_queries = [
                    str(item.get("query", "")).strip()
                    for item in raw_queries[:query_limit]
                    if isinstance(item, dict)
                ]
                recovery_queries = fallback_queries(
                    primary_query,
                    *original_queries,
                )

                for recovery_query in recovery_queries:
                    print(
                        f"[RECOVERY] {scene_id}: "
                        f"{recovery_query}"
                    )
                    for provider_name in (
                        "openverse",
                        "wikimedia",
                        "pixabay",
                    ):
                        if (
                            provider_name == "pixabay"
                            and self.pixabay is None
                        ):
                            continue
                        candidates.extend(
                            self._search_provider(
                                provider_name=provider_name,
                                query=recovery_query,
                                limit=candidates_per_query,
                            )
                        )

                    if candidates:
                        break

            ranked = rerank_candidates(
                query=primary_query,
                candidates=candidates,
            )

            if not ranked:
                attempted = fallback_queries(
                    primary_query,
                    *[
                        str(item.get("query", "")).strip()
                        for item in raw_queries[:query_limit]
                        if isinstance(item, dict)
                    ],
                )
                attempted_text = ", ".join(attempted[:6])
                raise MediaCollectorError(
                    f"{scene_id}: 무료 미디어 자동 재검색 후에도 "
                    "사용할 수 있는 후보가 없습니다. "
                    f"재검색어: {attempted_text or '없음'}"
                )

            selected: MediaCandidate | None = None
            local_path: Path | None = None
            download_errors: list[str] = []
            blocked_providers: set[str] = set()

            unused_ranked = [
                candidate
                for candidate in ranked
                if (
                    candidate.provider,
                    candidate.media_id,
                ) not in used_media
            ]

            for candidate in (
                unused_ranked or ranked
            ):
                if candidate.provider in blocked_providers:
                    continue

                try:
                    local_path = (
                        self.downloader.download(
                            candidate=candidate,
                            destination_dir=(
                                self.assets_dir
                            ),
                            scene_id=scene_id,
                        )
                    )
                    selected = candidate
                    used_media.add(
                        (
                            candidate.provider,
                            candidate.media_id,
                        )
                    )
                    break
                except MediaDownloadError as exc:
                    error_text = str(exc)

                    download_errors.append(
                        f"{candidate.provider}: "
                        f"{candidate.title} / {error_text}"
                    )

                    print(
                        f"[RETRY] {scene_id}: "
                        f"{candidate.provider} / "
                        f"{candidate.title}"
                    )

                    if (
                        "429" in error_text
                        or "Too Many Requests" in error_text
                    ):
                        blocked_providers.add(
                            candidate.provider
                        )
                        print(
                            f"[SKIP PROVIDER] {scene_id}: "
                            f"{candidate.provider} "
                            "rate limited"
                        )

            if (
                selected is None
                or local_path is None
            ):
                recovery_queries = fallback_queries(
                    primary_query,
                    *searched_queries,
                )
                print(
                    f"[RECOVERY DOWNLOAD] {scene_id}: "
                    "기존 후보 다운로드 실패, 새 후보 검색"
                )

                for recovery_query in recovery_queries:
                    recovery_candidates: list[MediaCandidate] = []
                    for provider_name in (
                        "wikimedia",
                        "openverse",
                        "pixabay",
                        "nasa",
                    ):
                        if (
                            provider_name == "pixabay"
                            and self.pixabay is None
                        ):
                            continue
                        if (
                            provider_name == "nasa"
                            and not should_use_nasa(recovery_query)
                        ):
                            continue
                        recovery_candidates.extend(
                            self._search_provider(
                                provider_name=provider_name,
                                query=recovery_query,
                                limit=candidates_per_query,
                                bypass_cache=True,
                                relaxed=True,
                            )
                        )

                    for candidate in rerank_candidates(
                        query=recovery_query,
                        candidates=recovery_candidates,
                    ):
                        identity = (
                            candidate.provider,
                            candidate.media_id,
                        )
                        if identity in used_media:
                            continue
                        try:
                            local_path = self.downloader.download(
                                candidate=candidate,
                                destination_dir=self.assets_dir,
                                scene_id=scene_id,
                            )
                            selected = candidate
                            used_media.add(identity)
                            break
                        except MediaDownloadError as exc:
                            download_errors.append(
                                f"{candidate.provider}: "
                                f"{candidate.title} / {exc}"
                            )
                            print(
                                f"[RECOVERY RETRY] {scene_id}: "
                                f"{candidate.provider} / {candidate.title}"
                            )

                    if selected is not None and local_path is not None:
                        break

            if (
                selected is None
                or local_path is None
            ):
                error_preview = "\n".join(download_errors[:8])
                raise MediaCollectorError(
                    f"{scene_id}: 기본 검색과 자동 복구 검색의 "
                    "미디어 후보 다운로드에 모두 실패했습니다.\n"
                    f"{error_preview}"
                )

            sha256 = (
                self.downloader.file_sha256(
                    local_path
                )
            )

            manifest.add_scene(
                scene_id=scene_id,
                query=selected.query,
                candidate=selected,
                local_path=local_path,
                sha256=sha256,
            )

            print(
                f"[OK] {scene_id}: "
                f"{selected.provider} / "
                f"{selected.title}"
            )

        return manifest.save(
            self.episode_dir
            / "media_manifest_v7.json"
        )

    def _search_provider(
        self,
        *,
        provider_name: str,
        query: str,
        limit: int,
        bypass_cache: bool = False,
        relaxed: bool = False,
    ) -> list[MediaCandidate]:
        cache_key = self.cache.build_key(
            provider_name,
            query,
            str(limit),
        )

        cached = (
            None
            if bypass_cache
            else self.cache.load_json(cache_key)
        )

        if cached is not None:
            raw_candidates = cached.get(
                "candidates"
            )

            if (
                isinstance(
                    raw_candidates,
                    list,
                )
                and raw_candidates
            ):
                return [
                    candidate_from_dict(
                        item
                    )
                    for item in raw_candidates
                    if isinstance(
                        item,
                        dict,
                    )
                ]

        if provider_name == "wikimedia":
            candidates = (
                self.wikimedia.search(
                    query=query,
                    limit=limit,
                    min_width=720 if relaxed else 1080,
                    min_height=480 if relaxed else 1080,
                    allow_blocked_title_terms=relaxed,
                )
            )
        elif provider_name == "nasa":
            candidates = self.nasa.search(
                query=query,
                limit=limit,
            )
        elif provider_name == "openverse":
            candidates = self.openverse.search(
                query=query,
                limit=limit,
                min_width=720 if relaxed else 640,
                min_height=480,
            )
        elif (
            provider_name == "pixabay"
            and self.pixabay is not None
        ):
            candidates = self.pixabay.search(
                query=query,
                limit=limit,
            )
        else:
            candidates = []

        self.cache.save_json(
            cache_key,
            {
                "provider": provider_name,
                "query": query,
                "candidates": [
                    candidate_to_dict(
                        candidate
                    )
                    for candidate in candidates
                ],
            },
        )

        return candidates


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Release 7 Media Collector"
        )
    )
    parser.add_argument(
        "--episode",
        required=True,
    )
    parser.add_argument(
        "--force",
        action="store_true",
    )
    parser.add_argument(
        "--query-limit",
        type=int,
        default=5,
    )
    parser.add_argument(
        "--candidates-per-query",
        type=int,
        default=20,
    )
    return parser


def normalize_episode_id(
    value: str,
) -> str:
    normalized = value.strip().lower()

    if normalized.startswith("ep"):
        number_text = normalized[2:]
    else:
        number_text = normalized

    if not number_text.isdigit():
        raise MediaCollectorError(
            "에피소드 형식이 올바르지 않습니다."
        )

    return f"ep{int(number_text):03d}"


def main() -> int:
    parser = build_parser()
    arguments = parser.parse_args()

    try:
        episode_id = normalize_episode_id(
            arguments.episode
        )
        output_path = MediaCollector(
            episode_id=episode_id
        ).collect(
            force=arguments.force,
            query_limit=arguments.query_limit,
            candidates_per_query=(
                arguments.candidates_per_query
            ),
        )
    except Exception as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )
        return 1

    print(
        "[성공] Media Collector 완료"
    )
    print(
        f"Manifest: {output_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
