from __future__ import annotations

import copy
import json
import shutil
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

SOURCE_EPISODE = "ep025"
TARGET_EPISODE = "ep026"

EPISODES_DIR = ROOT / "projects" / "episodes"
SOURCE_DIR = EPISODES_DIR / SOURCE_EPISODE
TARGET_DIR = EPISODES_DIR / TARGET_EPISODE


TITLE = "비행기 창문에\n구멍이 있는 이유"

YOUTUBE_TITLE = "비행기 창문에 작은 구멍이 있는 진짜 이유"

DESCRIPTION = """비행기 창문을 자세히 보면
아래쪽에 아주 작은 구멍이 있습니다.

깨지거나 잘못 만들어진 것이 아니라
비행 중 창문 사이의 압력을 조절하는 장치입니다.

이 구멍 덕분에 바깥쪽 창문이
대부분의 압력 차를 견디게 되고,
중간 창문은 비상시를 위한 보호층으로 남습니다.

창문 사이의 습기를 배출해
김과 성에가 생기는 것도 줄여줍니다.

#비행기 #비행기창문 #항공기 #생활상식 #과학 #세계한입
"""

PINNED_COMMENT = """비행기 창문의 작은 구멍,
지금까지 발견한 적 있으셨나요?

다음 비행기에서 꼭 한번 확인해 보세요.
"""

TAGS = [
    "비행기",
    "비행기창문",
    "항공기",
    "항공상식",
    "생활상식",
    "과학상식",
    "압력",
    "기압",
    "비행",
    "여행",
    "세계한입",
]


SCENES = [
    {
        "id": "scene_001",
        "duration": 5.5,
        "text": (
            "비행기 창문을 자세히 보면 "
            "아래쪽에 작은 구멍이 있습니다."
        ),
        "query": "airplane passenger window bleed hole close up",
        "queries": [
            "airplane passenger window bleed hole close up",
            "aircraft window tiny hole close up",
            "airplane window breather hole",
        ],
    },
    {
        "id": "scene_002",
        "duration": 6.0,
        "text": (
            "혹시 창문이 깨진 것은 아닐까 "
            "불안해할 필요는 없습니다."
        ),
        "query": "passenger looking at airplane window close up",
        "queries": [
            "passenger looking at airplane window close up",
            "airplane cabin window passenger seat",
            "commercial airplane window interior",
        ],
    },
    {
        "id": "scene_003",
        "duration": 7.0,
        "text": (
            "비행기 창문은 보통 여러 겹으로 만들어지고, "
            "이 구멍은 중간 창에 있습니다."
        ),
        "query": "aircraft passenger window multiple panes diagram",
        "queries": [
            "aircraft passenger window multiple panes diagram",
            "airplane window layers cross section",
            "aircraft window pane structure",
        ],
    },
    {
        "id": "scene_004",
        "duration": 7.0,
        "text": (
            "비행기가 높이 올라가면 기내와 바깥의 "
            "공기 압력 차이가 크게 벌어집니다."
        ),
        "query": "commercial airplane flying high altitude exterior",
        "queries": [
            "commercial airplane flying high altitude exterior",
            "passenger aircraft above clouds",
            "airliner cruising altitude sky",
        ],
    },
    {
        "id": "scene_005",
        "duration": 7.5,
        "text": (
            "작은 구멍은 창문 사이의 압력을 조절해 "
            "바깥쪽 창이 압력을 견디게 합니다."
        ),
        "query": "airplane window pressure layers animation",
        "queries": [
            "airplane window pressure layers animation",
            "aircraft window cabin pressure diagram",
            "airplane window bleed hole pressure explanation",
        ],
    },
    {
        "id": "scene_006",
        "duration": 7.0,
        "text": (
            "또한 창문 사이의 습기를 배출해 "
            "김이나 성에가 생기는 것도 줄여줍니다."
        ),
        "query": "airplane window condensation frost close up",
        "queries": [
            "airplane window condensation frost close up",
            "aircraft window fog condensation",
            "airplane window ice crystals close up",
        ],
    },
    {
        "id": "scene_007",
        "duration": 6.0,
        "text": (
            "결국 작은 구멍 하나가 안전과 시야를 "
            "동시에 지키고 있었던 것입니다."
        ),
        "query": "clear airplane window view clouds passenger cabin",
        "queries": [
            "clear airplane window view clouds passenger cabin",
            "airplane window wing view above clouds",
            "passenger aircraft window clear sky",
        ],
    },
]


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

DURATION_KEYS = {
    "duration",
    "duration_seconds",
    "length",
    "length_seconds",
}

START_KEYS = {
    "start",
    "start_time",
    "start_seconds",
}

TITLE_KEYS = {
    "title",
    "headline",
    "display_title",
}


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8-sig") as file:
        return json.load(file)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )
        file.write("\n")


def replace_episode_id(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace(
            SOURCE_EPISODE,
            TARGET_EPISODE,
        )

    if isinstance(value, list):
        return [
            replace_episode_id(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: replace_episode_id(item)
            for key, item in value.items()
        }

    return value


def find_scene_list(node: Any) -> list[dict[str, Any]] | None:
    if isinstance(node, dict):
        for key in (
            "scenes",
            "timeline",
            "items",
            "segments",
            "shots",
        ):
            value = node.get(key)

            if (
                isinstance(value, list)
                and value
                and all(isinstance(item, dict) for item in value)
            ):
                return value

        for value in node.values():
            result = find_scene_list(value)

            if result is not None:
                return result

    if isinstance(node, list):
        for value in node:
            result = find_scene_list(value)

            if result is not None:
                return result

    return None


def update_scene(
    template: dict[str, Any],
    scene_data: dict[str, Any],
    start_time: float,
) -> dict[str, Any]:
    result = copy.deepcopy(template)

    def walk(node: Any, parent_key: str = "") -> Any:
        if isinstance(node, dict):
            updated: dict[str, Any] = {}

            for key, value in node.items():
                lowered = key.lower()

                if lowered in {"id", "scene_id", "sceneid"}:
                    updated[key] = scene_data["id"]

                elif lowered in TEXT_KEYS:
                    updated[key] = scene_data["text"]

                elif lowered in TITLE_KEYS:
                    updated[key] = TITLE

                elif lowered in DURATION_KEYS:
                    updated[key] = scene_data["duration"]

                elif lowered in START_KEYS:
                    updated[key] = start_time

                elif lowered in QUERY_KEYS:
                    if isinstance(value, list):
                        updated[key] = copy.deepcopy(
                            scene_data["queries"]
                        )
                    else:
                        updated[key] = scene_data["query"]

                elif lowered in {
                    "queries",
                    "search_queries",
                    "media_queries",
                    "keywords",
                }:
                    updated[key] = copy.deepcopy(
                        scene_data["queries"]
                    )

                else:
                    updated[key] = walk(value, key)

            return updated

        if isinstance(node, list):
            return [
                walk(item, parent_key)
                for item in node
            ]

        if isinstance(node, str):
            return node.replace(
                SOURCE_EPISODE,
                TARGET_EPISODE,
            )

        return node

    return walk(result)


def update_metadata(node: Any, total_duration: float) -> Any:
    if isinstance(node, list):
        return [
            update_metadata(item, total_duration)
            for item in node
        ]

    if not isinstance(node, dict):
        return node

    result: dict[str, Any] = {}

    for key, value in node.items():
        lowered = key.lower()

        if lowered in {
            "episode",
            "episode_id",
            "episodeid",
            "project_id",
        }:
            result[key] = TARGET_EPISODE

        elif lowered in {
            "total_duration",
            "totalduration",
            "total_duration_seconds",
        }:
            result[key] = total_duration

        elif lowered in TITLE_KEYS:
            result[key] = TITLE

        else:
            result[key] = update_metadata(
                value,
                total_duration,
            )

    return result


def create_timeline() -> None:
    source_path = SOURCE_DIR / "timeline.json"

    if not source_path.exists():
        raise FileNotFoundError(
            f"기준 파일이 없습니다: {source_path}"
        )

    timeline = replace_episode_id(
        read_json(source_path)
    )

    scene_list = find_scene_list(timeline)

    if scene_list is None or not scene_list:
        raise RuntimeError(
            "기준 timeline에서 장면 목록을 찾지 못했습니다."
        )

    templates = copy.deepcopy(scene_list)
    generated: list[dict[str, Any]] = []

    start_time = 0.0

    for index, scene_data in enumerate(SCENES):
        template = templates[
            min(index, len(templates) - 1)
        ]

        generated.append(
            update_scene(
                template,
                scene_data,
                start_time,
            )
        )

        start_time += float(scene_data["duration"])

    scene_list.clear()
    scene_list.extend(generated)

    timeline = update_metadata(
        timeline,
        start_time,
    )

    write_json(
        TARGET_DIR / "timeline.json",
        timeline,
    )


def create_story() -> None:
    story = {
        "episode_id": TARGET_EPISODE,
        "category": "everyday_science",
        "language": "ko",
        "title": TITLE,
        "youtube_title": YOUTUBE_TITLE,
        "youtube_description": DESCRIPTION,
        "pinned_comment": PINNED_COMMENT,
        "tags": TAGS,
        "estimated_duration": sum(
            scene["duration"]
            for scene in SCENES
        ),
        "scenes": [
            {
                "id": scene["id"],
                "duration": scene["duration"],
                "title": TITLE,
                "script": scene["text"],
                "caption": scene["text"],
                "tts": scene["text"],
                "media_query": scene["query"],
                "media_queries": scene["queries"],
            }
            for scene in SCENES
        ],
        "sources": [
            {
                "title": (
                    "Why do airplane windows "
                    "have a hole in them?"
                ),
                "topic": (
                    "Aircraft-window bleed hole, "
                    "pressure equalization and moisture"
                ),
            }
        ],
    }

    write_json(
        TARGET_DIR / "story.json",
        story,
    )


def create_metadata() -> None:
    metadata = {
        "episode_id": TARGET_EPISODE,
        "youtube": {
            "title": YOUTUBE_TITLE,
            "description": DESCRIPTION,
            "pinned_comment": PINNED_COMMENT,
            "tags": TAGS,
        },
        "title_layout": {
            "text": TITLE,
            "max_lines": 2,
            "color": "#7BFEB4",
        },
        "caption_policy": {
            "tts_equals_caption": True,
            "language": "ko",
            "preferred_lines": 1,
            "maximum_lines": 2,
        },
    }

    write_json(
        TARGET_DIR / "metadata.json",
        metadata,
    )


def main() -> None:
    if TARGET_DIR.exists():
        shutil.rmtree(TARGET_DIR)

    TARGET_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    create_timeline()
    create_story()
    create_metadata()

    print("=" * 60)
    print("EP026 새 주제 적용 완료")
    print("=" * 60)
    print(f"제목: {TITLE.replace(chr(10), ' / ')}")
    print(f"장면: {len(SCENES)}개")
    print(
        "길이: "
        f"{sum(scene['duration'] for scene in SCENES):.1f}초"
    )
    print(f"저장: {TARGET_DIR}")
    print()
    print("기존 사하라 이미지와 이전 TTS는 삭제되었습니다.")
    print()
    print("[다음 명령]")
    print(
        "py factory_runner.py "
        "--episode ep026 --validate-only"
    )
    print(
        "py factory_runner.py "
        "--episode ep026"
    )


if __name__ == "__main__":
    main()
