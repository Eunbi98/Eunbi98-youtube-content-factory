from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path.cwd()

EPISODE_ID = "ep026"

EPISODE_DIR = (
    ROOT
    / "projects"
    / "episodes"
    / EPISODE_ID
)

ASSETS_DIR = EPISODE_DIR / "assets"

REMOTION_PUBLIC_DIR = (
    ROOT
    / "projects"
    / "remotion"
    / "public"
)

OUTPUT_DIR = (
    ROOT
    / "projects"
    / "output"
)


SCENE_MEDIA = {
    "scene_001": {
        "text": (
            "비행기 창문을 자세히 보면 "
            "아래쪽에 작은 구멍이 있습니다."
        ),
        "query": (
            "airplane passenger window "
            "close up inside cabin"
        ),
        "queries": [
            "airplane passenger window close up inside cabin",
            "aircraft cabin window close up",
            "commercial airplane passenger window",
            "plane window interior close up",
            "airliner cabin window passenger seat",
        ],
    },
    "scene_002": {
        "text": (
            "혹시 창문이 깨진 것은 아닐까 "
            "불안해할 필요는 없습니다."
        ),
        "query": (
            "airplane cabin passenger "
            "looking through window"
        ),
        "queries": [
            "airplane cabin passenger looking through window",
            "aircraft passenger seat window interior",
            "commercial airplane cabin window",
            "passenger beside airplane window",
            "plane interior window seat",
        ],
    },
    "scene_003": {
        "text": (
            "비행기 창문은 보통 여러 겹으로 만들어지고, "
            "이 구멍은 중간 창에 있습니다."
        ),
        "query": (
            "commercial aircraft "
            "passenger window close up"
        ),
        "queries": [
            "commercial aircraft passenger window close up",
            "airplane window frame inside cabin",
            "airliner passenger window interior",
            "aircraft cabin window detail",
            "plane window frame close up",
        ],
    },
    "scene_004": {
        "text": (
            "비행기가 높이 올라가면 기내와 바깥의 "
            "공기 압력 차이가 크게 벌어집니다."
        ),
        "query": (
            "commercial airplane "
            "flying above clouds"
        ),
        "queries": [
            "commercial airplane flying above clouds",
            "airliner cruising above clouds",
            "passenger jet high altitude sky",
            "commercial aircraft exterior clouds",
            "airplane flight above cloud layer",
        ],
    },
    "scene_005": {
        "text": (
            "작은 구멍은 창문 사이의 압력을 조절해 "
            "바깥쪽 창이 압력을 견디게 합니다."
        ),
        "query": (
            "airplane passenger window "
            "close up cabin"
        ),
        "queries": [
            "airplane passenger window close up cabin",
            "commercial airplane window interior",
            "aircraft window passenger seat close up",
            "airliner cabin window detail",
            "plane passenger window frame",
        ],
    },
    "scene_006": {
        "text": (
            "또한 창문 사이의 습기를 배출해 "
            "김이나 성에가 생기는 것도 줄여줍니다."
        ),
        "query": (
            "airplane window "
            "cloud view close up"
        ),
        "queries": [
            "airplane window cloud view close up",
            "aircraft passenger window clouds",
            "plane window view from cabin",
            "commercial flight window sky",
            "airliner window above clouds",
        ],
    },
    "scene_007": {
        "text": (
            "결국 작은 구멍 하나가 안전과 시야를 "
            "동시에 지키고 있었던 것입니다."
        ),
        "query": (
            "airplane wing through "
            "passenger window"
        ),
        "queries": [
            "airplane wing through passenger window",
            "aircraft wing view from window seat",
            "commercial airplane window wing clouds",
            "plane window view wing sunset",
            "airliner wing above clouds passenger view",
        ],
    },
}


TEXT_KEYS = {
    "text",
    "script",
    "caption",
    "subtitle",
    "narration",
    "tts",
    "tts_text",
    "voiceover",
    "voice_over",
    "content",
}

QUERY_KEYS = {
    "query",
    "search_query",
    "media_query",
    "image_query",
    "video_query",
}

QUERY_LIST_KEYS = {
    "queries",
    "search_queries",
    "media_queries",
    "image_queries",
    "video_queries",
    "keywords",
}


def read_json(path: Path) -> Any:
    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as file:
        return json.load(file)


def write_json(
    path: Path,
    data: Any,
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def detect_scene_id(
    node: dict[str, Any],
) -> str | None:
    for key in (
        "id",
        "scene_id",
        "sceneId",
    ):
        value = node.get(key)

        if not isinstance(value, str):
            continue

        normalized = value.lower()

        if normalized in SCENE_MEDIA:
            return normalized

    return None


def update_node(
    node: Any,
    active_scene: str | None = None,
) -> Any:
    if isinstance(node, list):
        return [
            update_node(
                item,
                active_scene,
            )
            for item in node
        ]

    if not isinstance(node, dict):
        return node

    detected_scene = detect_scene_id(node)
    current_scene = detected_scene or active_scene

    result: dict[str, Any] = {}

    for key, value in node.items():
        lowered = key.lower()

        if current_scene in SCENE_MEDIA:
            scene_data = SCENE_MEDIA[current_scene]

            if lowered in TEXT_KEYS:
                result[key] = scene_data["text"]
                continue

            if lowered in QUERY_KEYS:
                if isinstance(value, list):
                    result[key] = scene_data["queries"]
                else:
                    result[key] = scene_data["query"]

                continue

            if lowered in QUERY_LIST_KEYS:
                result[key] = scene_data["queries"]
                continue

        result[key] = update_node(
            value,
            current_scene,
        )

    return result


def patch_json_files() -> None:
    paths = [
        EPISODE_DIR / "timeline.json",
        EPISODE_DIR / "story.json",
        EPISODE_DIR / "metadata.json",
    ]

    updated_count = 0

    for path in paths:
        if not path.exists():
            continue

        original = read_json(path)
        updated = update_node(original)

        write_json(
            path,
            updated,
        )

        print(
            f"[검색어 수정] {path}"
        )

        updated_count += 1

    if updated_count == 0:
        raise FileNotFoundError(
            "EP026에서 수정 가능한 JSON 파일을 "
            "찾지 못했습니다."
        )


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)

        print(
            f"[폴더 삭제] {path}"
        )

    elif path.is_file():
        path.unlink()

        print(
            f"[파일 삭제] {path}"
        )


def clear_episode_assets() -> None:
    if ASSETS_DIR.exists():
        remove_path(ASSETS_DIR)

    ASSETS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    cache_files = [
        "media_manifest.json",
        "timeline.json.media.json",
        "media.json",
        "assets_manifest.json",
        "render_result.json",
        "download_manifest.json",
    ]

    for filename in cache_files:
        path = EPISODE_DIR / filename

        if path.exists():
            remove_path(path)

    for dirname in (
        "render",
        "output",
        "cache",
        "downloads",
    ):
        path = EPISODE_DIR / dirname

        if path.exists():
            remove_path(path)


def clear_remotion_public() -> None:
    if not REMOTION_PUBLIC_DIR.exists():
        return

    patterns = [
        "scene_*.jpg",
        "scene_*.jpeg",
        "scene_*.png",
        "scene_*.webp",
        "scene_*.mp4",
    ]

    for pattern in patterns:
        for path in REMOTION_PUBLIC_DIR.glob(pattern):
            remove_path(path)

    copied_json_files = [
        "timeline.json",
        "story.json",
        "metadata.json",
        "media_manifest.json",
    ]

    for filename in copied_json_files:
        path = REMOTION_PUBLIC_DIR / filename

        if path.exists():
            remove_path(path)


def clear_old_video() -> None:
    candidates = [
        OUTPUT_DIR / "ep026.mp4",
        ROOT / "output" / "ep026.mp4",
        (
            ROOT
            / "projects"
            / "remotion"
            / "output"
            / "ep026.mp4"
        ),
    ]

    for path in candidates:
        if path.exists():
            remove_path(path)

    if OUTPUT_DIR.exists():
        for path in OUTPUT_DIR.glob("*ep026*.mp4"):
            remove_path(path)


def print_queries() -> None:
    print()
    print("=" * 64)
    print("EP026 비행기 이미지 검색어")
    print("=" * 64)

    for scene_id, data in SCENE_MEDIA.items():
        print(
            f"{scene_id}: {data['query']}"
        )


def main() -> None:
    if not EPISODE_DIR.exists():
        raise FileNotFoundError(
            f"EP026 폴더가 없습니다: {EPISODE_DIR}"
        )

    print("=" * 64)
    print("EP026 비행기 이미지 중심으로 재설정")
    print("=" * 64)

    patch_json_files()
    clear_episode_assets()
    clear_remotion_public()
    clear_old_video()
    print_queries()

    print()
    print("=" * 64)
    print("수정 완료")
    print("=" * 64)
    print(
        "이제 Factory Runner를 실행하면 "
        "모든 장면 이미지를 새로 수집합니다."
    )
    print()
    print(
        "py factory_runner.py "
        "--episode ep026"
    )


if __name__ == "__main__":
    main()
