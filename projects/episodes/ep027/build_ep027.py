from __future__ import annotations

import json
from pathlib import Path
from typing import Any


EPISODE_ID = "ep027"
FPS = 30

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = PROJECT_ROOT / "projects" / "episodes" / EPISODE_ID
ASSETS_DIR = EPISODE_DIR / "assets"
OUTPUT_DIR = PROJECT_ROOT / "projects" / "output"

TIMELINE_PATH = EPISODE_DIR / "timeline.json"
MEDIA_MANIFEST_PATH = EPISODE_DIR / "media_manifest.json"
STORY_PATH = EPISODE_DIR / "story.json"
YOUTUBE_PATH = EPISODE_DIR / "youtube.json"


def scene(
    scene_id: str,
    start: float,
    duration: float,
    title: str,
    narration: str,
    media_query: str,
    *,
    effect: str = "zoom-in",
) -> dict[str, Any]:
    english_keywords = [
        keyword.strip()
        for keyword in media_query.split()
        if keyword.strip()
    ]

    return {
        "id": scene_id,
        "start": start,
        "duration": duration,
        "title": title,
        "caption": narration,
        "narration": narration,

        # Scene Query Generator가 우선 확인하는 영문 키워드
        "keywords": english_keywords,

        "media": {
            "type": "image",
            "src": f"{scene_id}.jpg",
            "query": media_query,
            "keywords": english_keywords,
        },

        "mediaSearch": {
            "sourceKeywords": english_keywords,
        },

        "effect": {
            "type": effect,
            "intensity": 0.025,
        },
        "transition": {
            "type": "fade",
            "duration": 0.6,
        },
    }  


def build_scenes() -> list[dict[str, Any]]:
    return [
        scene(
            "scene_001",
            0.0,
            4.2,
            "블랙홀은 모두\n은하 중심에 있을까?",
            "블랙홀은 모두 은하 중심에만 있을까요?",
            "supermassive black hole galaxy space NASA",
        ),
        scene(
            "scene_002",
            4.2,
            5.2,
            "예상 밖의 장소에서\n발견된 블랙홀",
            "최근 NASA가 전혀 예상하지 못한 곳에서 거대한 블랙홀을 발견했습니다.",
            "wandering black hole outside galaxy artist concept",
            effect="pan-left",
        ),
        scene(
            "scene_003",
            9.4,
            5.4,
            "은하 중심이 아닌\n외곽을 떠돌고 있었다",
            "이 블랙홀은 은하 중심이 아니라 은하 외곽을 홀로 떠돌고 있었습니다.",
            "galaxy outskirts wandering black hole illustration",
            effect="zoom-out",
        ),
        scene(
            "scene_004",
            14.8,
            5.0,
            "빛을 내지 않아\n보이지 않았던 존재",
            "평소에는 빛을 내지 않아 존재조차 확인하기 어려웠습니다.",
            "invisible dormant black hole dark space illustration",
        ),
        scene(
            "scene_005",
            19.8,
            5.5,
            "별 하나가 너무 가까이\n접근했다",
            "하지만 근처를 지나던 별 하나가 블랙홀에 너무 가까이 접근했습니다.",
            "star approaching supermassive black hole tidal disruption",
            effect="pan-right",
        ),
        scene(
            "scene_006",
            25.3,
            5.5,
            "강력한 중력이\n별을 찢어버렸다",
            "강력한 중력은 별을 산산조각 냈고 별의 잔해는 뜨겁게 빛나기 시작했습니다.",
            "tidal disruption event star shredded black hole NASA",
        ),
        scene(
            "scene_007",
            30.8,
            5.0,
            "스위프트 망원경이\n그 순간을 포착했다",
            "NASA의 스위프트 우주망원경은 이 순간을 포착했습니다.",
            "NASA Swift observatory space telescope illustration",
            effect="zoom-out",
        ),
        scene(
            "scene_008",
            35.8,
            6.5,
            "은하 충돌로 밀려난\n블랙홀일 가능성",
            "과학자들은 은하끼리 충돌하는 과정에서 블랙홀이 중심 밖으로 밀려났을 가능성을 보고 있습니다.",
            "colliding galaxies supermassive black hole simulation",
            effect="pan-left",
        ),
        scene(
            "scene_009",
            42.3,
            5.7,
            "우주에는 얼마나 많은\n떠돌이 블랙홀이 있을까?",
            "우리가 보지 못하는 떠돌이 블랙홀은 우주에 얼마나 더 존재할까요?",
            "deep space galaxy field black holes universe",
            effect="zoom-out",
        ),
    ]


def build_timeline(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    total_duration = max(
        float(item["start"]) + float(item["duration"])
        for item in scenes
    )

    return {
        "episodeId": EPISODE_ID,
        "fps": FPS,
        "width": 1080,
        "height": 1920,
        "duration": total_duration,
        "title": "은하 밖을 떠돌던\n블랙홀의 정체",
        "theme": {
            "backgroundColor": "#17212D",
            "titleColor": "#7BFEB4",
            "captionColor": "#FFFFFF",
            "captionStrokeColor": "#000000",
            "fontFamily": "Pretendard",
        },
        "audio": {
            "src": "narration.mp3",
        },
        "scenes": scenes,
    }


def build_story(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "episode_id": EPISODE_ID,
        "category": "space",
        "topic": "은하 밖을 떠돌던 블랙홀이 별을 삼킨 사건",
        "title": "은하 밖을 떠돌던 블랙홀의 정체",
        "hook": "블랙홀은 모두 은하 중심에만 있을까요?",
        "source": {
            "publisher": "NASA",
            "published_at": "2026-07-27",
            "article_title": (
                "NASA’s Swift Sees ‘Wandering’ "
                "Mega Black Hole Shredding Star"
            ),
        },
        "script": [item["narration"] for item in scenes],
    }


def build_media_manifest(
    scenes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "episode_id": EPISODE_ID,
        "assets_dir": str(ASSETS_DIR),
        "items": [
            {
                "scene_id": item["id"],
                "filename": f'{item["id"]}.jpg',
                "query": item["media"]["query"],
                "providers": [
                    "nasa",
                    "wikimedia",
                    "pexels",
                    "pixabay",
                ],
                "required": True,
            }
            for item in scenes
        ],
    }


def build_youtube_metadata() -> dict[str, Any]:
    return {
        "title": "은하 밖을 떠돌던 블랙홀이 별을 삼켰다",
        "description": (
            "블랙홀은 은하 중심에만 존재한다고 생각하기 쉽습니다.\n\n"
            "하지만 NASA의 스위프트 우주망원경은 은하 외곽을 떠돌던 "
            "초대질량 블랙홀이 별을 산산조각 내는 순간을 포착했습니다.\n\n"
            "평소에는 보이지 않던 블랙홀이 별을 삼키며 빛을 내자 "
            "그동안 숨겨져 있던 위치가 드러난 것입니다.\n\n"
            "#우주 #블랙홀 #NASA #과학 #세계한입"
        ),
        "tags": [
            "블랙홀",
            "떠돌이 블랙홀",
            "초대질량 블랙홀",
            "NASA",
            "스위프트 우주망원경",
            "조석 파괴 사건",
            "우주",
            "천문학",
            "과학",
            "세계한입",
        ],
        "pinned_comment": (
            "은하 중심 밖을 떠도는 블랙홀이 발견됐습니다. "
            "우주에는 아직 발견하지 못한 떠돌이 블랙홀이 "
            "얼마나 더 있을까요?"
        ),
    }


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def main() -> None:
    EPISODE_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    scenes = build_scenes()

    save_json(
        TIMELINE_PATH,
        build_timeline(scenes),
    )
    save_json(
        STORY_PATH,
        build_story(scenes),
    )
    save_json(
        MEDIA_MANIFEST_PATH,
        build_media_manifest(scenes),
    )
    save_json(
        YOUTUBE_PATH,
        build_youtube_metadata(),
    )

    print("=" * 58)
    print(" EP027 패키지 생성 완료")
    print("=" * 58)
    print(f" Story:   {STORY_PATH}")
    print(f" Timeline:{TIMELINE_PATH}")
    print(f" Manifest:{MEDIA_MANIFEST_PATH}")
    print(f" YouTube: {YOUTUBE_PATH}")
    print(f" Assets:  {ASSETS_DIR}")
    print()
    print("다음 실행:")
    print(
        "py factory_runner.py "
        "--episode ep027 "
        "--validate-only"
    )


if __name__ == "__main__":
    main()