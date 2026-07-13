from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


MEDIA_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MEDIA_DIR.parents[1]
DIRECTOR_DIR = PROJECT_ROOT / "projects" / "director"

for module_path in (
    MEDIA_DIR,
    DIRECTOR_DIR,
):
    module_path_text = str(module_path)

    if module_path_text not in sys.path:
        sys.path.insert(
            0,
            module_path_text,
        )


from base_provider import (  # noqa: E402
    MediaCandidate,
    MediaProvider,
    MediaSearchRequest,
)
from provider_registry import (  # noqa: E402
    MediaProviderRegistry,
    ProviderRegistryError,
)
from search_prompt import (  # noqa: E402
    SearchPromptError,
    build_scene_search_prompt,
)
from wikimedia_provider import (  # noqa: E402
    WikimediaProvider,
    WikimediaProviderError,
)


class MediaCollectorError(RuntimeError):
    """장면별 미디어 자동 수집 오류입니다."""


@dataclass(
    frozen=True,
    slots=True,
)
class CollectorScene:
    scene_id: str
    title: str
    narration: str
    keywords: tuple[str, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class CandidateSearchHit:
    candidate: MediaCandidate
    query: str
    query_priority: int
    final_score: float


@dataclass(
    frozen=True,
    slots=True,
)
class SceneCollectionResult:
    scene_id: str
    query: str
    output_path: Path
    candidate: MediaCandidate
    reused: bool
    searched_queries: tuple[str, ...]
    candidate_count: int
    searched_providers: tuple[str, ...]

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "sceneId": self.scene_id,
            "query": self.query,
            "searchedQueries": list(
                self.searched_queries
            ),
            "searchedProviders": list(
                self.searched_providers
            ),
            "candidateCount": (
                self.candidate_count
            ),
            "outputPath": str(
                self.output_path
            ),
            "reused": self.reused,
            "candidate": (
                self.candidate.to_dict()
            ),
        }


@dataclass(
    frozen=True,
    slots=True,
)
class MediaCollectionResult:
    episode_id: str
    timeline_path: Path
    assets_dir: Path
    manifest_path: Path
    collected_count: int
    reused_count: int
    results: tuple[
        SceneCollectionResult,
        ...,
    ]


def load_json_object(
    file_path: Path,
) -> dict[str, Any]:
    resolved_path = file_path.resolve()

    if not resolved_path.exists():
        raise MediaCollectorError(
            "JSON 파일을 찾을 수 없습니다:\n"
            f"{resolved_path}"
        )

    if not resolved_path.is_file():
        raise MediaCollectorError(
            "JSON 경로가 파일이 아닙니다:\n"
            f"{resolved_path}"
        )

    try:
        raw_data = json.loads(
            resolved_path.read_text(
                encoding="utf-8",
            )
        )

    except json.JSONDecodeError as exc:
        raise MediaCollectorError(
            "JSON 형식이 올바르지 않습니다.\n"
            f"파일: {resolved_path}\n"
            f"줄: {exc.lineno}\n"
            f"열: {exc.colno}\n"
            f"원인: {exc.msg}"
        ) from exc

    except OSError as exc:
        raise MediaCollectorError(
            "JSON 파일을 읽지 못했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc

    if not isinstance(
        raw_data,
        dict,
    ):
        raise MediaCollectorError(
            "JSON 최상위 데이터는 객체여야 합니다.\n"
            f"파일: {resolved_path}"
        )

    return raw_data


def save_json_object(
    *,
    payload: dict[str, Any],
    output_path: Path,
) -> None:
    resolved_path = output_path.resolve()

    resolved_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

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
            )
            + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(
            resolved_path
        )

    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink()

        raise MediaCollectorError(
            "JSON 파일 저장에 실패했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc


def normalize_episode_id(
    raw_episode_id: str,
) -> str:
    normalized = (
        raw_episode_id
        .strip()
        .lower()
    )

    if not normalized:
        raise MediaCollectorError(
            "episode ID가 비어 있습니다."
        )

    return normalized


def read_episode_id(
    *,
    timeline_data: dict[str, Any],
    timeline_path: Path,
) -> str:
    raw_episode_id = timeline_data.get(
        "episodeId"
    )

    if isinstance(
        raw_episode_id,
        str,
    ):
        normalized = (
            raw_episode_id
            .strip()
            .lower()
        )

        if normalized:
            return normalized

    return normalize_episode_id(
        timeline_path.parent.name
    )


def normalize_text(
    raw_value: object,
) -> str:
    if not isinstance(
        raw_value,
        str,
    ):
        return ""

    return " ".join(
        raw_value
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )


def normalize_keywords(
    raw_keywords: object,
) -> tuple[str, ...]:
    if not isinstance(
        raw_keywords,
        list,
    ):
        return ()

    keywords: list[str] = []
    seen: set[str] = set()

    for raw_keyword in raw_keywords:
        if not isinstance(
            raw_keyword,
            str,
        ):
            continue

        normalized = normalize_text(
            raw_keyword
        )

        if not normalized:
            continue

        lowered = normalized.lower()

        if lowered in seen:
            continue

        seen.add(lowered)
        keywords.append(
            normalized
        )

    return tuple(keywords)


def read_scene_keywords(
    raw_scene: dict[str, Any],
) -> tuple[str, ...]:
    direct_keywords = normalize_keywords(
        raw_scene.get("keywords")
    )

    if direct_keywords:
        return direct_keywords

    raw_media = raw_scene.get(
        "media"
    )

    if isinstance(
        raw_media,
        dict,
    ):
        media_keywords = normalize_keywords(
            raw_media.get("keywords")
        )

        if media_keywords:
            return media_keywords

    raw_media_search = raw_scene.get(
        "mediaSearch"
    )

    if isinstance(
        raw_media_search,
        dict,
    ):
        source_keywords = normalize_keywords(
            raw_media_search.get(
                "sourceKeywords"
            )
        )

        if source_keywords:
            return source_keywords

        raw_queries = raw_media_search.get(
            "queries"
        )

        if isinstance(
            raw_queries,
            list,
        ):
            query_keywords: list[str] = []

            for raw_query in raw_queries:
                if isinstance(
                    raw_query,
                    str,
                ):
                    query = normalize_text(
                        raw_query
                    )

                elif isinstance(
                    raw_query,
                    dict,
                ):
                    query = normalize_text(
                        raw_query.get("query")
                    )

                else:
                    continue

                if query:
                    query_keywords.append(
                        query
                    )

            if query_keywords:
                return tuple(
                    query_keywords
                )

    return ()


def parse_timeline_scenes(
    timeline_data: dict[str, Any],
) -> list[CollectorScene]:
    raw_scenes = timeline_data.get(
        "scenes"
    )

    if not isinstance(
        raw_scenes,
        list,
    ):
        raise MediaCollectorError(
            "Timeline의 scenes 필드가 "
            "배열이 아닙니다."
        )

    if not raw_scenes:
        raise MediaCollectorError(
            "Timeline에 장면이 없습니다."
        )

    scenes: list[CollectorScene] = []
    seen_scene_ids: set[str] = set()

    for index, raw_scene in enumerate(
        raw_scenes,
        start=1,
    ):
        if not isinstance(
            raw_scene,
            dict,
        ):
            raise MediaCollectorError(
                f"{index}번째 장면이 "
                "객체 형식이 아닙니다."
            )

        raw_scene_id = raw_scene.get(
            "id"
        )

        if not isinstance(
            raw_scene_id,
            str,
        ):
            raise MediaCollectorError(
                f"{index}번째 장면의 id가 "
                "문자열이 아닙니다."
            )

        scene_id = raw_scene_id.strip()

        if not scene_id:
            raise MediaCollectorError(
                f"{index}번째 장면의 id가 "
                "비어 있습니다."
            )

        if scene_id in seen_scene_ids:
            raise MediaCollectorError(
                "중복된 장면 ID가 있습니다: "
                f"{scene_id}"
            )

        seen_scene_ids.add(
            scene_id
        )

        title = normalize_text(
            raw_scene.get("title")
        )

        narration = normalize_text(
            raw_scene.get("narration")
        )

        if not narration:
            narration = normalize_text(
                raw_scene.get("caption")
            )

        keywords = read_scene_keywords(
            raw_scene
        )

        if (
            not title
            and not narration
            and not keywords
        ):
            raise MediaCollectorError(
                f"{scene_id}: 검색에 사용할 "
                "title, narration, keywords가 "
                "모두 비어 있습니다."
            )

        scenes.append(
            CollectorScene(
                scene_id=scene_id,
                title=title,
                narration=narration,
                keywords=keywords,
            )
        )

    return scenes


def find_raw_scene(
    *,
    timeline_data: dict[str, Any],
    scene_id: str,
) -> dict[str, Any]:
    raw_scenes = timeline_data.get(
        "scenes"
    )

    if not isinstance(
        raw_scenes,
        list,
    ):
        raise MediaCollectorError(
            "Timeline scenes를 읽을 수 없습니다."
        )

    for raw_scene in raw_scenes:
        if (
            isinstance(
                raw_scene,
                dict,
            )
            and raw_scene.get("id")
            == scene_id
        ):
            return raw_scene

    raise MediaCollectorError(
        "Timeline에서 장면을 찾을 수 없습니다: "
        f"{scene_id}"
    )


def contains_latin_text(
    text: str,
) -> bool:
    return bool(
        re.search(
            r"[A-Za-z]",
            text,
        )
    )


def build_search_queries(
    *,
    scene: CollectorScene,
    max_queries: int,
) -> tuple[str, ...]:
    try:
        prompt = build_scene_search_prompt(
            scene_id=scene.scene_id,
            title=scene.title,
            narration=scene.narration,
            keywords=scene.keywords,
            max_queries=max_queries,
        )

    except (
        SearchPromptError,
        ValueError,
    ) as exc:
        raise MediaCollectorError(
            f"{scene.scene_id}: 검색어 생성에 "
            "실패했습니다.\n"
            f"원인: {exc}"
        ) from exc

    queries: list[str] = []
    seen: set[str] = set()

    for query_item in prompt.queries:
        query = normalize_text(
            query_item.query
        )

        if not query:
            continue

        normalized_key = query.lower()

        if normalized_key in seen:
            continue

        seen.add(
            normalized_key
        )

        queries.append(
            query
        )

    if not queries:
        raise MediaCollectorError(
            f"{scene.scene_id}: 생성된 검색어가 "
            "없습니다."
        )

    has_english_query = any(
        contains_latin_text(
            query
        )
        for query in queries
    )

    if not has_english_query:
        print(
            "       [경고] 검색어가 모두 "
            "한국어입니다."
        )

    return tuple(
        queries
    )


def tokenize_search_text(
    text: str,
) -> set[str]:
    return {
        token.lower()
        for token in re.findall(
            r"[A-Za-z0-9가-힣]+",
            text,
        )
        if len(token) >= 2
    }


def calculate_title_relevance(
    *,
    candidate: MediaCandidate,
    query: str,
) -> float:
    query_tokens = tokenize_search_text(
        query
    )

    if not query_tokens:
        return 0.0

    candidate_tokens = tokenize_search_text(
        " ".join(
            value
            for value in (
                candidate.title,
                candidate.author or "",
            )
            if value
        )
    )

    if not candidate_tokens:
        return 0.0

    matched_tokens = (
        query_tokens
        & candidate_tokens
    )

    match_ratio = (
        len(matched_tokens)
        / len(query_tokens)
    )

    return round(
        match_ratio * 30,
        3,
    )


def calculate_orientation_score(
    *,
    candidate: MediaCandidate,
    requested_orientation: str,
) -> float:
    if requested_orientation == "any":
        if (
            candidate.orientation
            == "portrait"
        ):
            return 10.0

        if (
            candidate.orientation
            == "square"
        ):
            return 7.0

        return 5.0

    if (
        candidate.orientation
        == requested_orientation
    ):
        return 25.0

    if (
        requested_orientation
        == "portrait"
        and candidate.orientation
        == "square"
    ):
        return 8.0

    return 0.0


def calculate_resolution_score(
    candidate: MediaCandidate,
) -> float:
    pixel_count = (
        candidate.width
        * candidate.height
    )

    if pixel_count >= 16_000_000:
        return 28.0

    if pixel_count >= 12_000_000:
        return 25.0

    if pixel_count >= 8_000_000:
        return 21.0

    if pixel_count >= 4_000_000:
        return 17.0

    if pixel_count >= 2_000_000:
        return 12.0

    if pixel_count > 0:
        return 5.0

    return 0.0


def calculate_candidate_score(
    *,
    candidate: MediaCandidate,
    query: str,
    requested_orientation: str,
    query_priority: int,
) -> float:
    score = float(
        candidate.score
    )

    score += calculate_resolution_score(
        candidate
    )

    score += calculate_orientation_score(
        candidate=candidate,
        requested_orientation=(
            requested_orientation
        ),
    )

    score += calculate_title_relevance(
        candidate=candidate,
        query=query,
    )

    if candidate.license_name:
        score += 8.0

    if candidate.license_url:
        score += 4.0

    if candidate.author:
        score += 3.0

    if candidate.thumbnail_url:
        score += 2.0

    score += max(
        0.0,
        12.0
        - (
            (query_priority - 1)
            * 2.0
        ),
    )

    return round(
        score,
        3,
    )


def deduplicate_candidate_hits(
    hits: Sequence[
        CandidateSearchHit
    ],
) -> list[CandidateSearchHit]:
    best_by_identity: dict[
        tuple[str, str],
        CandidateSearchHit,
    ] = {}

    for hit in hits:
        candidate_key = (
            hit.candidate.provider,
            hit.candidate.media_id,
        )

        existing = (
            best_by_identity.get(
                candidate_key
            )
        )

        if (
            existing is None
            or hit.final_score
            > existing.final_score
        ):
            best_by_identity[
                candidate_key
            ] = hit

    unique_hits: list[
        CandidateSearchHit
    ] = []

    seen_download_urls: set[str] = set()

    for hit in sorted(
        best_by_identity.values(),
        key=lambda item: (
            -item.final_score,
            -(
                item.candidate.width
                * item.candidate.height
            ),
        ),
    ):
        download_url = (
            hit.candidate.download_url
        )

        if (
            download_url
            in seen_download_urls
        ):
            continue

        seen_download_urls.add(
            download_url
        )

        unique_hits.append(
            hit
        )

    return unique_hits


def collect_candidate_hits(
    *,
    registry: MediaProviderRegistry,
    queries: Sequence[str],
    orientation: str,
    candidates_per_query: int,
    min_width: int,
    min_height: int,
    provider_names: Sequence[str] | None,
) -> tuple[
    list[CandidateSearchHit],
    tuple[str, ...],
]:
    all_hits: list[
        CandidateSearchHit
    ] = []

    searched_queries: list[str] = []

    for query_index, query in enumerate(
        queries,
        start=1,
    ):
        searched_queries.append(
            query
        )

        print(
            f"       검색 "
            f"[{query_index}/{len(queries)}]: "
            f"{query}"
        )

        request = MediaSearchRequest(
            query=query,
            media_kind="image",
            orientation=orientation,
            max_results=(
                candidates_per_query
            ),
            min_width=min_width,
            min_height=min_height,
            safe_search=True,
        )

        try:
            search_result = registry.search(
                request,
                provider_names=(
                    provider_names
                ),
                continue_on_error=True,
                deduplicate=True,
            )

        except ProviderRegistryError as exc:
            print(
                "       [검색 실패] "
                f"{exc}"
            )
            continue

        for failure in (
            search_result.failures
        ):
            print(
                "       [Provider 실패] "
                f"{failure.provider}: "
                f"{failure.message}"
            )

        candidates = list(
            search_result.candidates
        )

        if not candidates:
            print(
                "       [결과 없음]"
            )
            continue

        provider_counts: dict[
            str,
            int,
        ] = {}

        for candidate in candidates:
            provider_counts[
                candidate.provider
            ] = (
                provider_counts.get(
                    candidate.provider,
                    0,
                )
                + 1
            )

        provider_summary = ", ".join(
            f"{name} {count}개"
            for name, count
            in sorted(
                provider_counts.items()
            )
        )

        print(
            "       [후보] "
            f"{len(candidates)}개 "
            f"({provider_summary})"
        )

        for candidate in candidates:
            final_score = (
                calculate_candidate_score(
                    candidate=candidate,
                    query=query,
                    requested_orientation=(
                        orientation
                    ),
                    query_priority=(
                        query_index
                    ),
                )
            )

            all_hits.append(
                CandidateSearchHit(
                    candidate=(
                        candidate.with_score(
                            final_score
                        )
                    ),
                    query=query,
                    query_priority=(
                        query_index
                    ),
                    final_score=(
                        final_score
                    ),
                )
            )

    return (
        deduplicate_candidate_hits(
            all_hits
        ),
        tuple(
            searched_queries
        ),
    )


def select_best_candidate_hit(
    hits: Sequence[
        CandidateSearchHit
    ],
) -> CandidateSearchHit:
    if not hits:
        raise MediaCollectorError(
            "선택할 미디어 후보가 없습니다."
        )

    return max(
        hits,
        key=lambda hit: (
            hit.final_score,
            hit.candidate.width
            * hit.candidate.height,
            -hit.query_priority,
        ),
    )


def choose_output_extension(
    candidate: MediaCandidate,
) -> str:
    extension = (
        candidate.file_extension
        or "jpg"
    )

    normalized = (
        extension
        .strip()
        .lower()
        .lstrip(".")
    )

    if normalized in {
        "jpeg",
        "jpe",
    }:
        return "jpg"

    if normalized == "tiff":
        return "tif"

    return normalized or "jpg"


def remove_old_scene_assets(
    *,
    assets_dir: Path,
    scene_id: str,
    keep_path: Path | None = None,
) -> None:
    for existing_path in assets_dir.glob(
        f"{scene_id}.*"
    ):
        if (
            keep_path is not None
            and existing_path.resolve()
            == keep_path.resolve()
        ):
            continue

        if existing_path.is_file():
            existing_path.unlink()


def build_manifest_path(
    episode_dir: Path,
) -> Path:
    return (
        episode_dir
        / "media_manifest.json"
    )


def update_timeline_scene_media(
    *,
    timeline_data: dict[str, Any],
    scene_result: SceneCollectionResult,
) -> None:
    raw_scene = find_raw_scene(
        timeline_data=timeline_data,
        scene_id=scene_result.scene_id,
    )

    raw_media = raw_scene.get(
        "media"
    )

    media = (
        raw_media
        if isinstance(
            raw_media,
            dict,
        )
        else {}
    )

    media["type"] = "image"
    media["src"] = (
        scene_result
        .output_path
        .name
    )

    media.setdefault(
        "fit",
        "cover",
    )

    media.setdefault(
        "position",
        "center center",
    )

    raw_scene["media"] = media

    raw_scene["mediaSource"] = {
        "provider": (
            scene_result
            .candidate
            .provider
        ),
        "mediaId": (
            scene_result
            .candidate
            .media_id
        ),
        "query": (
            scene_result.query
        ),
        "searchedQueries": list(
            scene_result
            .searched_queries
        ),
        "searchedProviders": list(
            scene_result
            .searched_providers
        ),
        "candidateCount": (
            scene_result
            .candidate_count
        ),
        "sourceUrl": (
            scene_result
            .candidate
            .source_url
        ),
        "downloadUrl": (
            scene_result
            .candidate
            .download_url
        ),
        "author": (
            scene_result
            .candidate
            .author
        ),
        "authorUrl": (
            scene_result
            .candidate
            .author_url
        ),
        "licenseName": (
            scene_result
            .candidate
            .license_name
        ),
        "licenseUrl": (
            scene_result
            .candidate
            .license_url
        ),
        "width": (
            scene_result
            .candidate
            .width
        ),
        "height": (
            scene_result
            .candidate
            .height
        ),
        "orientation": (
            scene_result
            .candidate
            .orientation
        ),
        "score": (
            scene_result
            .candidate
            .score
        ),
    }


class TimelineMediaCollector:
    """
    Timeline 장면별로 여러 Provider를 검색하고
    가장 높은 점수의 이미지를 다운로드합니다.

    provider 인수는 기존 Runner와의 호환을 위해
    유지합니다. 신규 코드는 registry 사용을 권장합니다.
    """

    def __init__(
        self,
        *,
        registry: (
            MediaProviderRegistry
            | None
        ) = None,
        provider: (
            MediaProvider
            | None
        ) = None,
    ) -> None:
        if (
            registry is not None
            and provider is not None
        ):
            raise ValueError(
                "registry와 provider는 "
                "동시에 지정할 수 없습니다."
            )

        if registry is not None:
            self.registry = registry

        elif provider is not None:
            self.registry = (
                MediaProviderRegistry(
                    providers=[
                        provider,
                    ]
                )
            )

        else:
            raise ValueError(
                "registry 또는 provider 중 "
                "하나는 반드시 필요합니다."
            )

    def collect(
        self,
        *,
        timeline_path: Path,
        assets_dir: Path | None = None,
        orientation: str = "any",
        max_search_queries: int = 5,
        candidates_per_query: int = 8,
        min_width: int = 720,
        min_height: int = 720,
        overwrite: bool = False,
        update_timeline: bool = True,
        scene_ids: Sequence[str] | None = None,
        provider_names: Sequence[str] | None = None,
    ) -> MediaCollectionResult:
        if max_search_queries <= 0:
            raise MediaCollectorError(
                "max_search_queries는 "
                "1 이상이어야 합니다."
            )

        if candidates_per_query <= 0:
            raise MediaCollectorError(
                "candidates_per_query는 "
                "1 이상이어야 합니다."
            )

        available_provider_names = (
            self.registry
            .list_provider_names(
                media_kind="image"
            )
        )

        if not available_provider_names:
            raise MediaCollectorError(
                "등록된 이미지 Provider가 없습니다."
            )

        if provider_names:
            searched_provider_names = tuple(
                provider_name.strip().lower()
                for provider_name
                in provider_names
                if provider_name.strip()
            )
        else:
            searched_provider_names = (
                available_provider_names
            )

        resolved_timeline_path = (
            timeline_path.resolve()
        )

        timeline_data = load_json_object(
            resolved_timeline_path
        )

        episode_id = read_episode_id(
            timeline_data=timeline_data,
            timeline_path=(
                resolved_timeline_path
            ),
        )

        episode_dir = (
            resolved_timeline_path.parent
        )

        resolved_assets_dir = (
            assets_dir.resolve()
            if assets_dir is not None
            else episode_dir / "assets"
        )

        resolved_assets_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        scenes = parse_timeline_scenes(
            timeline_data
        )

        requested_scene_ids = {
            scene_id.strip()
            for scene_id in (
                scene_ids or ()
            )
            if scene_id.strip()
        }

        if requested_scene_ids:
            scenes = [
                scene
                for scene in scenes
                if scene.scene_id
                in requested_scene_ids
            ]

            missing_scene_ids = (
                requested_scene_ids
                - {
                    scene.scene_id
                    for scene in scenes
                }
            )

            if missing_scene_ids:
                raise MediaCollectorError(
                    "Timeline에서 요청한 장면을 "
                    "찾을 수 없습니다: "
                    + ", ".join(
                        sorted(
                            missing_scene_ids
                        )
                    )
                )

        if not scenes:
            raise MediaCollectorError(
                "수집할 장면이 없습니다."
            )

        collected_count = 0
        reused_count = 0

        results: list[
            SceneCollectionResult
        ] = []

        print("=" * 72)
        print(
            " YouTube Content Factory "
            "Multi Provider Media Collector"
        )
        print("=" * 72)
        print(
            f"{'episode':>18}: "
            f"{episode_id}"
        )
        print(
            f"{'timeline':>18}: "
            f"{resolved_timeline_path}"
        )
        print(
            f"{'assets':>18}: "
            f"{resolved_assets_dir}"
        )
        print(
            f"{'providers':>18}: "
            + ", ".join(
                searched_provider_names
            )
        )
        print(
            f"{'scene_count':>18}: "
            f"{len(scenes)}"
        )
        print("-" * 72)

        for scene_index, scene in enumerate(
            scenes,
            start=1,
        ):
            print(
                f"[{scene_index}/{len(scenes)}] "
                f"{scene.scene_id}"
            )

            queries = build_search_queries(
                scene=scene,
                max_queries=(
                    max_search_queries
                ),
            )

            hits, searched_queries = (
                collect_candidate_hits(
                    registry=self.registry,
                    queries=queries,
                    orientation=orientation,
                    candidates_per_query=(
                        candidates_per_query
                    ),
                    min_width=min_width,
                    min_height=min_height,
                    provider_names=(
                        searched_provider_names
                    ),
                )
            )

            if not hits:
                query_preview = "\n".join(
                    f"  - {query}"
                    for query
                    in searched_queries
                )

                raise MediaCollectorError(
                    f"{scene.scene_id}: 모든 검색어와 "
                    "Provider에서 사용 가능한 "
                    "이미지를 찾지 못했습니다.\n"
                    "사용한 검색어:\n"
                    f"{query_preview}\n"
                    "Provider:\n"
                    f"  - "
                    + "\n  - ".join(
                        searched_provider_names
                    )
                )

            selected_hit = (
                select_best_candidate_hit(
                    hits
                )
            )

            selected_candidate = (
                selected_hit.candidate
            )

            selected_provider = (
                self.registry.get(
                    selected_candidate.provider
                )
            )

            extension = (
                choose_output_extension(
                    selected_candidate
                )
            )

            output_path = (
                resolved_assets_dir
                / (
                    f"{scene.scene_id}."
                    f"{extension}"
                )
            )

            existed_before = (
                output_path.exists()
                and output_path
                .stat()
                .st_size
                > 0
                and not overwrite
            )

            remove_old_scene_assets(
                assets_dir=(
                    resolved_assets_dir
                ),
                scene_id=scene.scene_id,
                keep_path=(
                    output_path
                    if existed_before
                    else None
                ),
            )

            download_result = (
                selected_provider.download(
                    candidate=(
                        selected_candidate
                    ),
                    output_path=output_path,
                    overwrite=overwrite,
                )
            )

            scene_result = (
                SceneCollectionResult(
                    scene_id=scene.scene_id,
                    query=(
                        selected_hit.query
                    ),
                    output_path=(
                        download_result
                        .output_path
                    ),
                    candidate=(
                        selected_candidate
                    ),
                    reused=existed_before,
                    searched_queries=(
                        searched_queries
                    ),
                    candidate_count=len(
                        hits
                    ),
                    searched_providers=(
                        searched_provider_names
                    ),
                )
            )

            results.append(
                scene_result
            )

            if existed_before:
                reused_count += 1
            else:
                collected_count += 1

            if update_timeline:
                update_timeline_scene_media(
                    timeline_data=timeline_data,
                    scene_result=scene_result,
                )

            print(
                f"       전체 후보: "
                f"{len(hits)}개"
            )
            print(
                f"       선택 Provider: "
                f"{selected_candidate.provider}"
            )
            print(
                f"       선택 검색어: "
                f"{selected_hit.query}"
            )
            print(
                f"       선택: "
                f"{selected_candidate.title}"
            )
            print(
                f"       크기: "
                f"{selected_candidate.width}x"
                f"{selected_candidate.height}"
            )
            print(
                f"       방향: "
                f"{selected_candidate.orientation}"
            )
            print(
                f"       점수: "
                f"{selected_candidate.score:.3f}"
            )
            print(
                f"       파일: "
                f"{scene_result.output_path.name}"
            )

        if update_timeline:
            backup_path = (
                resolved_timeline_path
                .with_suffix(
                    ".json.media.bak"
                )
            )

            shutil.copy2(
                resolved_timeline_path,
                backup_path,
            )

            save_json_object(
                payload=timeline_data,
                output_path=(
                    resolved_timeline_path
                ),
            )

        manifest_path = build_manifest_path(
            episode_dir
        )

        manifest_payload: dict[
            str,
            Any,
        ] = {
            "version": "1.2",
            "episodeId": episode_id,
            "providers": list(
                searched_provider_names
            ),
            "timelinePath": str(
                resolved_timeline_path
            ),
            "assetsDirectory": str(
                resolved_assets_dir
            ),
            "collectedCount": (
                collected_count
            ),
            "reusedCount": (
                reused_count
            ),
            "sceneCount": len(
                results
            ),
            "results": [
                result.to_dict()
                for result in results
            ],
        }

        save_json_object(
            payload=manifest_payload,
            output_path=manifest_path,
        )

        return MediaCollectionResult(
            episode_id=episode_id,
            timeline_path=(
                resolved_timeline_path
            ),
            assets_dir=(
                resolved_assets_dir
            ),
            manifest_path=manifest_path,
            collected_count=(
                collected_count
            ),
            reused_count=reused_count,
            results=tuple(
                results
            ),
        )


def resolve_timeline_path(
    *,
    episode_id: str,
    timeline_argument: str | None,
) -> Path:
    if timeline_argument:
        return Path(
            timeline_argument
        )

    return (
        PROJECT_ROOT
        / "projects"
        / "episodes"
        / episode_id
        / "timeline.json"
    )


def resolve_assets_dir(
    assets_argument: str | None,
) -> Path | None:
    if not assets_argument:
        return None

    return Path(
        assets_argument
    )


def build_argument_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Timeline의 각 장면에 맞는 이미지를 "
            "등록된 Media Provider에서 검색하고 "
            "자동 다운로드합니다."
        )
    )

    parser.add_argument(
        "--episode",
        default="ep008",
    )

    parser.add_argument(
        "--timeline",
        default=None,
    )

    parser.add_argument(
        "--assets-dir",
        default=None,
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
        "--max-search-queries",
        type=int,
        default=5,
    )

    parser.add_argument(
        "--candidates-per-query",
        type=int,
        default=8,
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
        "--scene",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--provider",
        action="append",
        default=[],
        help=(
            "사용할 Provider 이름입니다. "
            "여러 번 지정할 수 있습니다."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
    )

    parser.add_argument(
        "--no-update-timeline",
        action="store_true",
    )

    return parser


def print_summary(
    result: MediaCollectionResult,
) -> None:
    print("-" * 72)
    print(
        "[완료] Timeline 미디어 자동 수집"
    )
    print(
        f"{'전체 장면':>18}: "
        f"{len(result.results)}"
    )
    print(
        f"{'신규 다운로드':>18}: "
        f"{result.collected_count}"
    )
    print(
        f"{'기존 재사용':>18}: "
        f"{result.reused_count}"
    )
    print(
        f"{'Assets':>18}: "
        f"{result.assets_dir}"
    )
    print(
        f"{'Manifest':>18}: "
        f"{result.manifest_path}"
    )
    print(
        f"{'Timeline':>18}: "
        f"{result.timeline_path}"
    )


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    timeline_path = resolve_timeline_path(
        episode_id=(
            arguments.episode
        ),
        timeline_argument=(
            arguments.timeline
        ),
    )

    assets_dir = resolve_assets_dir(
        arguments.assets_dir
    )

    provider = WikimediaProvider()

    registry = MediaProviderRegistry(
        providers=[
            provider,
        ]
    )

    try:
        collector = TimelineMediaCollector(
            registry=registry
        )

        result = collector.collect(
            timeline_path=timeline_path,
            assets_dir=assets_dir,
            orientation=(
                arguments.orientation
            ),
            max_search_queries=(
                arguments
                .max_search_queries
            ),
            candidates_per_query=(
                arguments
                .candidates_per_query
            ),
            min_width=(
                arguments.min_width
            ),
            min_height=(
                arguments.min_height
            ),
            overwrite=(
                arguments.overwrite
            ),
            update_timeline=(
                not arguments
                .no_update_timeline
            ),
            scene_ids=(
                arguments.scene
            ),
            provider_names=(
                arguments.provider
                or None
            ),
        )

    except (
        MediaCollectorError,
        ProviderRegistryError,
        WikimediaProviderError,
        SearchPromptError,
        ValueError,
        OSError,
    ) as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )

        return 1

    finally:
        provider.close()

    print_summary(
        result
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )