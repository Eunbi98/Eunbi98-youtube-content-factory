import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
EPISODE_DIR = ROOT / "projects" / "episodes" / "ep026"

FILES = [
    EPISODE_DIR / "timeline.json",
    EPISODE_DIR / "story.json",
]

SCENE_UPDATES = {
    "scene_005": {
        "text": (
            "작은 구멍은 창문 사이의 압력을 조절해 "
            "바깥쪽 창이 압력을 견디게 합니다."
        ),
        "query": "airplane window close up passenger cabin",
        "queries": [
            "airplane window close up passenger cabin",
            "commercial airplane window interior",
            "aircraft passenger window close up",
            "airplane cabin window above clouds",
            "plane window from passenger seat",
        ],
    },
    # 다음 장면도 미리 검색 성공률이 높은 표현으로 변경
    "scene_006": {
        "text": (
            "또한 창문 사이의 습기를 배출해 "
            "김이나 성에가 생기는 것도 줄여줍니다."
        ),
        "query": "airplane window clouds close up",
        "queries": [
            "airplane window clouds close up",
            "aircraft window passenger view",
            "plane window above clouds",
            "airplane cabin window close up",
            "commercial flight window view",
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
    "keywords",
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def find_scene_id(node: dict[str, Any]) -> str | None:
    for key in ("id", "scene_id", "sceneId"):
        value = node.get(key)

        if isinstance(value, str):
            lowered = value.lower()

            if lowered in SCENE_UPDATES:
                return lowered

    return None


def update_node(
    node: Any,
    active_scene: str | None = None,
) -> Any:
    if isinstance(node, list):
        return [
            update_node(item, active_scene)
            for item in node
        ]

    if not isinstance(node, dict):
        return node

    detected_scene = find_scene_id(node)
    current_scene = detected_scene or active_scene

    result: dict[str, Any] = {}

    for key, value in node.items():
        lowered = key.lower()

        if current_scene in SCENE_UPDATES:
            update = SCENE_UPDATES[current_scene]

            if lowered in TEXT_KEYS:
                result[key] = update["text"]
                continue

            if lowered in QUERY_KEYS:
                if isinstance(value, list):
                    result[key] = update["queries"]
                else:
                    result[key] = update["query"]
                continue

            if lowered in QUERY_LIST_KEYS:
                result[key] = update["queries"]
                continue

        result[key] = update_node(
            value,
            current_scene,
        )

    return result


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
        print(f"[삭제] {path}")

    elif path.is_file():
        path.unlink()
        print(f"[삭제] {path}")


def clear_media_cache() -> None:
    assets_dir = EPISODE_DIR / "assets"

    if assets_dir.exists():
        for path in assets_dir.iterdir():
            name = path.name.lower()

            if (
                "scene_005" in name
                or "scene_006" in name
            ):
                remove_path(path)

    cache_files = [
        EPISODE_DIR / "media_manifest.json",
        EPISODE_DIR / "timeline.json.media.json",
        EPISODE_DIR / "media.json",
        EPISODE_DIR / "assets_manifest.json",
    ]

    for path in cache_files:
        if path.exists():
            remove_path(path)

    output_dirs = [
        EPISODE_DIR / "render",
        EPISODE_DIR / "output",
    ]

    for path in output_dirs:
        if path.exists():
            remove_path(path)


def main() -> None:
    for path in FILES:
        if not path.exists():
            continue

        data = read_json(path)
        updated = update_node(data)
        write_json(path, updated)

        print(f"[수정] {path.name}")

    clear_media_cache()

    print()
    print("=" * 60)
    print("scene_005 및 scene_006 검색어 수정 완료")
    print("=" * 60)
    print("scene_005: airplane window close up passenger cabin")
    print("scene_006: airplane window clouds close up")
    print()
    print("[다음 실행]")
    print("py factory_runner.py --episode ep026")


if __name__ == "__main__":
    main()
