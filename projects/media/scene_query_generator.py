from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence


MEDIA_DIR = Path(
    __file__
).resolve().parent

PROJECT_ROOT = MEDIA_DIR.parents[1]

DIRECTOR_DIR = (
    PROJECT_ROOT
    / "projects"
    / "director"
)

for module_path in (
    MEDIA_DIR,
    DIRECTOR_DIR,
):
    module_path_text = str(
        module_path
    )

    if module_path_text not in sys.path:
        sys.path.insert(
            0,
            module_path_text,
        )


from search_prompt import (  # noqa: E402
    SceneSearchPrompt,
    SearchPromptError,
    build_scene_search_prompt,
)


class SceneQueryGeneratorError(
    RuntimeError
):
    """Timeline 장면 검색어 생성 오류입니다."""


@dataclass(
    frozen=True,
    slots=True,
)
class TimelineScene:
    scene_id: str
    title: str
    narration: str
    keywords: tuple[str, ...]


@dataclass(
    frozen=True,
    slots=True,
)
class SceneQueryResult:
    episode_id: str
    timeline_path: Path
    output_path: Path
    scene_count: int
    prompts: tuple[
        SceneSearchPrompt,
        ...,
    ]


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
        normalized = normalize_text(
            raw_keyword
        )

        if not normalized:
            continue

        identity = (
            normalized.casefold()
        )

        if identity in seen:
            continue

        seen.add(identity)
        keywords.append(normalized)

    return tuple(keywords)


def load_json_object(
    file_path: Path,
) -> dict[str, Any]:
    resolved_path = (
        file_path.resolve()
    )

    if not resolved_path.exists():
        raise SceneQueryGeneratorError(
            "JSON 파일을 찾을 수 없습니다:\n"
            f"{resolved_path}"
        )

    if not resolved_path.is_file():
        raise SceneQueryGeneratorError(
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
        raise SceneQueryGeneratorError(
            "JSON 형식이 올바르지 않습니다.\n"
            f"파일: {resolved_path}\n"
            f"줄: {exc.lineno}\n"
            f"열: {exc.colno}\n"
            f"원인: {exc.msg}"
        ) from exc
    except OSError as exc:
        raise SceneQueryGeneratorError(
            "JSON 파일을 읽지 못했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc

    if not isinstance(
        raw_data,
        dict,
    ):
        raise SceneQueryGeneratorError(
            "JSON 최상위 데이터는 "
            "객체여야 합니다.\n"
            f"파일: {resolved_path}"
        )

    return raw_data


def save_json_object(
    *,
    payload: dict[str, Any],
    output_path: Path,
) -> None:
    resolved_path = (
        output_path.resolve()
    )

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
            ) + "\n",
            encoding="utf-8",
        )

        temporary_path.replace(
            resolved_path
        )
    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink()

        raise SceneQueryGeneratorError(
            "검색어 JSON 저장에 실패했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc


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

    fallback = (
        timeline_path
        .parent
        .name
        .strip()
        .lower()
    )

    if not fallback:
        raise SceneQueryGeneratorError(
            "episode ID를 확인할 수 없습니다."
        )

    return fallback


def read_scene_keywords(
    raw_scene: dict[str, Any],
) -> tuple[str, ...]:
    keyword_sources: list[
        tuple[str, ...]
    ] = []

    keyword_sources.append(
        normalize_keywords(
            raw_scene.get("keywords")
        )
    )

    raw_media = raw_scene.get(
        "media"
    )

    if isinstance(
        raw_media,
        dict,
    ):
        keyword_sources.append(
            normalize_keywords(
                raw_media.get(
                    "keywords"
                )
            )
        )

    raw_media_search = (
        raw_scene.get(
            "mediaSearch"
        )
    )

    if isinstance(
        raw_media_search,
        dict,
    ):
        keyword_sources.append(
            normalize_keywords(
                raw_media_search.get(
                    "sourceKeywords"
                )
            )
        )

        raw_queries = (
            raw_media_search.get(
                "queries"
            )
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
                        raw_query.get(
                            "query"
                        )
                    )
                else:
                    continue

                if query:
                    query_keywords.append(
                        query
                    )

            keyword_sources.append(
                tuple(query_keywords)
            )

    keywords: list[str] = []
    seen: set[str] = set()

    for source in keyword_sources:
        for keyword in source:
            identity = (
                keyword.casefold()
            )

            if identity in seen:
                continue

            seen.add(identity)
            keywords.append(keyword)

    return tuple(keywords)


def read_scene_narration(
    raw_scene: dict[str, Any],
) -> str:
    for field_name in (
        "narration",
        "caption",
        "script",
        "subtitle",
    ):
        narration = normalize_text(
            raw_scene.get(field_name)
        )

        if narration:
            return narration

    return ""


def parse_timeline_scenes(
    timeline_data: dict[str, Any],
) -> list[TimelineScene]:
    raw_scenes = timeline_data.get(
        "scenes"
    )

    if not isinstance(
        raw_scenes,
        list,
    ):
        raise SceneQueryGeneratorError(
            "Timeline의 scenes 필드가 "
            "배열이 아닙니다."
        )

    if not raw_scenes:
        raise SceneQueryGeneratorError(
            "Timeline에 장면이 없습니다."
        )

    scenes: list[TimelineScene] = []
    seen_scene_ids: set[str] = set()

    for index, raw_scene in enumerate(
        raw_scenes,
        start=1,
    ):
        if not isinstance(
            raw_scene,
            dict,
        ):
            raise SceneQueryGeneratorError(
                f"{index}번째 장면이 "
                "객체 형식이 아닙니다."
            )

        scene_id = normalize_text(
            raw_scene.get("id")
        )

        if not scene_id:
            raise SceneQueryGeneratorError(
                f"{index}번째 장면의 "
                "id가 비어 있습니다."
            )

        if scene_id in seen_scene_ids:
            raise SceneQueryGeneratorError(
                "중복된 장면 ID가 있습니다: "
                f"{scene_id}"
            )

        seen_scene_ids.add(scene_id)

        title = normalize_text(
            raw_scene.get("title")
        )

        narration = (
            read_scene_narration(
                raw_scene
            )
        )

        keywords = read_scene_keywords(
            raw_scene
        )

        if (
            not title
            and not narration
            and not keywords
        ):
            raise SceneQueryGeneratorError(
                f"{scene_id}: 검색에 사용할 "
                "title, narration, keywords가 "
                "모두 비어 있습니다."
            )

        scenes.append(
            TimelineScene(
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
        raise SceneQueryGeneratorError(
            "Timeline scenes를 "
            "읽을 수 없습니다."
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

    raise SceneQueryGeneratorError(
        "Timeline에서 장면을 "
        "찾을 수 없습니다: "
        f"{scene_id}"
    )


def update_scene_media_search(
    *,
    timeline_data: dict[str, Any],
    prompt: SceneSearchPrompt,
) -> None:
    raw_scene = find_raw_scene(
        timeline_data=timeline_data,
        scene_id=prompt.scene_id,
    )

    raw_media_search = (
        raw_scene.get(
            "mediaSearch"
        )
    )

    media_search = (
        raw_media_search
        if isinstance(
            raw_media_search,
            dict,
        )
        else {}
    )

    media_search.update(
        {
            "version": "2.0",
            "primaryQuery": (
                prompt.primary_query
            ),
            "sourceKeywords": list(
                prompt.source_keywords
            ),
            "entities": list(
                prompt.entities
            ),
            "queries": [
                query.to_dict()
                for query in (
                    prompt.queries
                )
            ],
        }
    )

    raw_scene["mediaSearch"] = (
        media_search
    )


class SceneQueryGenerator:
    def generate(
        self,
        *,
        timeline_path: Path,
        output_path: Path | None = None,
        max_queries: int = 10,
        scene_ids: Sequence[str] | None = None,
        update_timeline: bool = True,
    ) -> SceneQueryResult:
        if max_queries < 1:
            raise SceneQueryGeneratorError(
                "max_queries는 "
                "1 이상이어야 합니다."
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

            found_scene_ids = {
                scene.scene_id
                for scene in scenes
            }

            missing_scene_ids = (
                requested_scene_ids
                - found_scene_ids
            )

            if missing_scene_ids:
                raise (
                    SceneQueryGeneratorError(
                        "Timeline에서 요청한 "
                        "장면을 찾을 수 없습니다: "
                        + ", ".join(
                            sorted(
                                missing_scene_ids
                            )
                        )
                    )
                )

        if not scenes:
            raise SceneQueryGeneratorError(
                "검색어를 생성할 장면이 "
                "없습니다."
            )

        prompts: list[
            SceneSearchPrompt
        ] = []

        for scene in scenes:
            try:
                prompt = (
                    build_scene_search_prompt(
                        scene_id=(
                            scene.scene_id
                        ),
                        title=scene.title,
                        narration=(
                            scene.narration
                        ),
                        keywords=(
                            scene.keywords
                        ),
                        max_queries=(
                            max_queries
                        ),
                    )
                )
            except SearchPromptError as exc:
                raise (
                    SceneQueryGeneratorError(
                        f"{scene.scene_id}: "
                        "Scene Query 생성에 "
                        "실패했습니다.\n"
                        f"원인: {exc}"
                    )
                ) from exc

            prompts.append(prompt)

            if update_timeline:
                update_scene_media_search(
                    timeline_data=(
                        timeline_data
                    ),
                    prompt=prompt,
                )

        resolved_output_path = (
            output_path.resolve()
            if output_path is not None
            else (
                resolved_timeline_path
                .parent
                / "media_queries.json"
            )
        )

        output_payload: dict[
            str,
            Any,
        ] = {
            "version": "2.0",
            "episodeId": episode_id,
            "timelinePath": str(
                resolved_timeline_path
            ),
            "sceneCount": len(prompts),
            "scenes": [
                prompt.to_dict()
                for prompt in prompts
            ],
        }

        save_json_object(
            payload=output_payload,
            output_path=(
                resolved_output_path
            ),
        )

        if update_timeline:
            backup_path = (
                resolved_timeline_path
                .with_suffix(
                    ".json.queries.bak"
                )
            )

            if not backup_path.exists():
                try:
                    backup_path.write_text(
                        resolved_timeline_path
                        .read_text(
                            encoding="utf-8"
                        ),
                        encoding="utf-8",
                    )
                except OSError as exc:
                    raise (
                        SceneQueryGeneratorError(
                            "Timeline 백업 저장에 "
                            "실패했습니다.\n"
                            f"파일: {backup_path}\n"
                            f"원인: {exc}"
                        )
                    ) from exc

            save_json_object(
                payload=timeline_data,
                output_path=(
                    resolved_timeline_path
                ),
            )

        return SceneQueryResult(
            episode_id=episode_id,
            timeline_path=(
                resolved_timeline_path
            ),
            output_path=(
                resolved_output_path
            ),
            scene_count=len(prompts),
            prompts=tuple(prompts),
        )


def normalize_episode_id(
    raw_episode_id: str,
) -> str:
    normalized = (
        raw_episode_id
        .strip()
        .lower()
    )

    if normalized.startswith("ep"):
        number_text = normalized[2:]
    else:
        number_text = normalized

    if not number_text.isdigit():
        raise SceneQueryGeneratorError(
            "에피소드 형식이 "
            "올바르지 않습니다. "
            "예: ep009 또는 009"
        )

    return (
        f"ep{int(number_text):03d}"
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


def resolve_output_path(
    output_argument: str | None,
) -> Path | None:
    if not output_argument:
        return None

    return Path(output_argument)


def build_argument_parser() -> (
    argparse.ArgumentParser
):
    parser = argparse.ArgumentParser(
        description=(
            "Timeline의 장면별 정보를 읽어 "
            "Wikimedia, NASA, Pixabay, "
            "Pexels용 영문 미디어 검색어를 "
            "자동 생성합니다."
        )
    )

    parser.add_argument(
        "--episode",
        default="ep009",
        help=(
            "에피소드 ID입니다. "
            "기본값: ep009"
        ),
    )

    parser.add_argument(
        "--timeline",
        default=None,
        help=(
            "timeline.json 경로입니다. "
            "생략하면 에피소드 폴더를 "
            "사용합니다."
        ),
    )

    parser.add_argument(
        "--output",
        default=None,
        help=(
            "media_queries.json 저장 "
            "경로입니다."
        ),
    )

    parser.add_argument(
        "--max-queries",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--scene",
        action="append",
        default=[],
        help=(
            "특정 장면만 생성합니다. "
            "여러 번 지정할 수 있습니다."
        ),
    )

    parser.add_argument(
        "--no-update-timeline",
        action="store_true",
        help=(
            "media_queries.json만 생성하고 "
            "timeline.json은 수정하지 "
            "않습니다."
        ),
    )

    return parser


def print_summary(
    result: SceneQueryResult,
) -> None:
    print("=" * 72)
    print(
        " YouTube Content Factory "
        "Release 7 Scene Query Generator"
    )
    print("=" * 72)

    print(
        f"{'episode':>18}: "
        f"{result.episode_id}"
    )

    print(
        f"{'timeline':>18}: "
        f"{result.timeline_path}"
    )

    print(
        f"{'output':>18}: "
        f"{result.output_path}"
    )

    print(
        f"{'scene_count':>18}: "
        f"{result.scene_count}"
    )

    print("-" * 72)

    for prompt in result.prompts:
        print(
            f"[{prompt.scene_id}] "
            f"{prompt.primary_query}"
        )

        for query in prompt.queries:
            print(
                f"  {query.priority:02d}. "
                f"{query.intent:<12} "
                f"{query.media_kind:<6} "
                f"{query.query}"
            )

    print("-" * 72)
    print(
        "[성공] Scene Query 생성 완료"
    )


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    try:
        episode_id = normalize_episode_id(
            arguments.episode
        )

        timeline_path = (
            resolve_timeline_path(
                episode_id=episode_id,
                timeline_argument=(
                    arguments.timeline
                ),
            )
        )

        output_path = resolve_output_path(
            arguments.output
        )

        result = (
            SceneQueryGenerator()
            .generate(
                timeline_path=(
                    timeline_path
                ),
                output_path=output_path,
                max_queries=(
                    arguments.max_queries
                ),
                scene_ids=(
                    arguments.scene
                ),
                update_timeline=(
                    not arguments
                    .no_update_timeline
                ),
            )
        )
    except (
        SceneQueryGeneratorError,
        SearchPromptError,
        OSError,
        ValueError,
    ) as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )
        return 1

    print_summary(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())