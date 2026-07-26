import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
EPISODE_DIR = ROOT / "projects" / "episodes" / "ep026"

TIMELINE_PATH = EPISODE_DIR / "timeline.json"
STORY_PATH = EPISODE_DIR / "story.json"

NEW_TEXT = (
    "비행기 창문은 보통 여러 겹으로 만들어지고, "
    "이 구멍은 중간 창에 있습니다."
)

NEW_QUERY = "airplane passenger window close up inside cabin"

NEW_QUERIES = [
    "airplane passenger window close up inside cabin",
    "commercial aircraft cabin window close up",
    "airplane window from passenger seat",
    "aircraft passenger window interior",
    "plane cabin window close up",
]

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


def is_scene_003(node: dict[str, Any]) -> bool:
    for key in ("id", "scene_id", "sceneId"):
        if str(node.get(key, "")).lower() == "scene_003":
            return True

    return False


def update_scene(node: Any, inside_scene_003: bool = False) -> Any:
    if isinstance(node, list):
        return [
            update_scene(item, inside_scene_003)
            for item in node
        ]

    if not isinstance(node, dict):
        return node

    current_scene = inside_scene_003 or is_scene_003(node)
    result: dict[str, Any] = {}

    for key, value in node.items():
        lowered = key.lower()

        if current_scene and lowered in QUERY_KEYS:
            if isinstance(value, list):
                result[key] = NEW_QUERIES
            else:
                result[key] = NEW_QUERY
            continue

        if current_scene and lowered in QUERY_LIST_KEYS:
            result[key] = NEW_QUERIES
            continue

        if current_scene and lowered in {
            "text",
            "script",
            "caption",
            "subtitle",
            "tts",
            "tts_text",
            "narration",
            "voiceover",
            "voice_over",
        }:
            result[key] = NEW_TEXT
            continue

        result[key] = update_scene(
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


def clear_scene_003_assets() -> None:
    assets_dir = EPISODE_DIR / "assets"

    if assets_dir.exists():
        for path in assets_dir.iterdir():
            if "scene_003" in path.name.lower():
                remove_path(path)

    possible_files = [
        EPISODE_DIR / "media_manifest.json",
        EPISODE_DIR / "timeline.json.media.json",
        EPISODE_DIR / "media.json",
        EPISODE_DIR / "assets_manifest.json",
    ]

    for path in possible_files:
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
    timeline = read_json(TIMELINE_PATH)
    timeline = update_scene(timeline)
    write_json(TIMELINE_PATH, timeline)

    print("[수정] timeline.json scene_003")

    if STORY_PATH.exists():
        story = read_json(STORY_PATH)
        story = update_scene(story)
        write_json(STORY_PATH, story)

        print("[수정] story.json scene_003")

    clear_scene_003_assets()

    print()
    print("=" * 60)
    print("scene_003 검색어 수정 완료")
    print("=" * 60)
    print(f"대표 검색어: {NEW_QUERY}")
    print()
    print("[다음 실행]")
    print("py factory_runner.py --episode ep026")


if __name__ == "__main__":
    main()
