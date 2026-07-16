from __future__ import annotations

import argparse
import json
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
from downloader import MediaDownloader  # noqa: E402
from manifest_builder import ManifestBuilder  # noqa: E402
from media_ranker import rerank_candidates  # noqa: E402
from provider_models import MediaCandidate  # noqa: E402
from providers.nasa_provider import NasaProvider  # noqa: E402
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
        self.wikimedia = (
            WikimediaProvider()
        )
        self.nasa = NasaProvider()
        self.downloader = (
            MediaDownloader()
        )
        self.api_keys = load_api_keys(
            PROJECT_ROOT
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

                candidates.extend(
                    self._search_provider(
                        provider_name="wikimedia",
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

            ranked = rerank_candidates(
                query=str(
                    raw_scene.get(
                        "primaryQuery",
                        "",
                    )
                ),
                candidates=candidates,
            )

            if not ranked:
                raise MediaCollectorError(
                    f"{scene_id}: 사용할 수 있는 "
                    "미디어 후보가 없습니다."
                )

            selected = ranked[0]
            local_path = (
                self.downloader.download(
                    candidate=selected,
                    destination_dir=(
                        self.assets_dir
                    ),
                    scene_id=scene_id,
                )
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
    ) -> list[MediaCandidate]:
        cache_key = self.cache.build_key(
            provider_name,
            query,
            str(limit),
        )

        cached = self.cache.load_json(
            cache_key
        )

        if cached is not None:
            raw_candidates = cached.get(
                "candidates"
            )

            if isinstance(
                raw_candidates,
                list,
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
                )
            )
        elif provider_name == "nasa":
            candidates = self.nasa.search(
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
