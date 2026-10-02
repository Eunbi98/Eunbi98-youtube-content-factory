from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any


EPISODE_ID = "ep028"
FPS = 30

PROJECT_ROOT = Path(__file__).resolve().parents[3]
EPISODE_DIR = PROJECT_ROOT / "projects" / "episodes" / EPISODE_ID
ASSETS_DIR = EPISODE_DIR / "assets"
OUTPUT_DIR = PROJECT_ROOT / "projects" / "output"

TIMELINE_PATH = EPISODE_DIR / "timeline.json"
MEDIA_MANIFEST_PATH = EPISODE_DIR / "media_manifest.json"
STORY_PATH = EPISODE_DIR / "story.json"
YOUTUBE_PATH = EPISODE_DIR / "youtube.json"
RUNNER_PATH = PROJECT_ROOT / "factory_runner.py"


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
    keywords = [
        keyword.strip()
        for keyword in media_query.split()
        if keyword.strip()
    ]

    return {
        "id": scene_id,
        "start": start,
        "duration": duration,
        "title": title,

        # 자막과 TTS는 반드시 동일
        "caption": narration,
        "narration": narration,

        "keywords": keywords,

        "media": {
            "type": "image",
            "src": f"{scene_id}.jpg",
            "query": media_query,
            "keywords": keywords,
        },

        "mediaSearch": {
            "sourceKeywords": keywords,
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
            4.3,
            "2천 년 된 콘크리트가\n아직도 버티는 이유",
            "2천 년 전에 만든 콘크리트가 지금도 무너지지 않고 남아 있습니다.",
            "Roman Pantheon ancient concrete dome Rome",
            effect="zoom-out",
        ),

        scene(
            "scene_002",
            4.3,
            5.0,
            "판테온과 항구를 만든\n로마의 콘크리트",
            "로마인들은 이 콘크리트로 판테온과 수로, 항구와 방파제를 건설했습니다.",
            "ancient Roman aqueduct harbor concrete ruins",
            effect="pan-left",
        ),

        scene(
            "scene_003",
            9.3,
            5.0,
            "첫 번째 비밀은\n화산재",
            "오랫동안 가장 중요한 비밀은 석회와 화산재를 섞은 재료라고 알려졌습니다.",
            "Pozzuoli volcanic ash Vesuvius Italy",
            effect="zoom-in",
        ),

        scene(
            "scene_004",
            14.3,
            5.4,
            "바닷물에 닿을수록\n더 단단해졌다",
            "특히 해양 콘크리트는 바닷물과 반응하며 안정적인 광물을 만들어 냈습니다.",
            "Roman underwater concrete harbor seawater ruins",
            effect="pan-right",
        ),

        scene(
            "scene_005",
            19.7,
            5.2,
            "하얀 석회 덩어리는\n실수가 아니었다",
            "그런데 연구진은 콘크리트 속 하얀 석회 덩어리가 단순한 제조 실수가 아니라는 사실을 발견했습니다.",
            "ancient Roman concrete limestone white mineral texture",
            effect="zoom-in",
        ),

        scene(
            "scene_006",
            24.9,
            5.8,
            "물이 들어오면\n균열을 스스로 메운다",
            "금이 생겨 물이 들어오면 석회 성분이 녹아 나와 새로운 광물로 굳으며 틈을 메웁니다.",
            "self healing concrete crack calcium carbonate",
            effect="zoom-out",
        ),

        scene(
            "scene_007",
            30.7,
            5.4,
            "2주 만에 균열이\n다시 막혔다",
            "실험에서는 로마 방식으로 만든 콘크리트의 균열이 약 2주 만에 막히는 모습도 확인됐습니다.",
            "concrete laboratory crack healing experiment",
            effect="pan-left",
        ),

        scene(
            "scene_008",
            36.1,
            5.5,
            "비밀은 하나가 아닌\n여러 반응의 조합",
            "최근에는 화산재와 석회뿐 아니라 탄산화 작용도 긴 수명에 영향을 주었을 가능성이 연구되고 있습니다.",
            "ancient Roman concrete scientific analysis laboratory",
            effect="zoom-in",
        ),

        scene(
            "scene_009",
            41.6,
            6.0,
            "현대 콘크리트도\n2천 년을 버틸 수 있을까?",
            "고대 로마의 기술은 더 오래가고 스스로 회복하는 현대 콘크리트의 단서가 되고 있습니다.",
            "modern sustainable concrete architecture future",
            effect="zoom-out",
        ),
    ]


def build_timeline(
    scenes: list[dict[str, Any]],
) -> dict[str, Any]:
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

        # 영상 전체 상단 제목
        "title": "2천 년을 버틴\n로마 콘크리트의 비밀",

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


def build_story(
    scenes: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "episode_id": EPISODE_ID,
        "category": "history_science",
        "topic": "2천 년을 버틴 고대 로마 콘크리트의 비밀",
        "title": "2천 년을 버틴 로마 콘크리트의 비밀",
        "hook": (
            "2천 년 전에 만든 콘크리트가 "
            "지금도 무너지지 않고 남아 있습니다."
        ),

        "source": {
            "publishers": [
                "MIT",
                "UC Berkeley",
            ],
            "research_topics": [
                "Roman concrete hot mixing",
                "lime clasts self-healing",
                "Roman marine concrete",
                "carbonation durability",
            ],
        },

        "script": [
            item["narration"]
            for item in scenes
        ],
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

                # 역사 소재이므로 Wikimedia 우선
                "providers": [
                    "wikimedia",
                    "pexels",
                    "pixabay",
                    "nasa",
                ],

                "required": True,
            }
            for item in scenes
        ],
    }


def build_youtube_metadata() -> dict[str, Any]:
    return {
        "title": "2천 년을 버틴 로마 콘크리트의 비밀",

        "description": (
            "고대 로마의 판테온과 항구, 수로에는 "
            "2천 년 가까이 버틴 콘크리트가 남아 있습니다.\n\n"
            "과거에는 화산재가 내구성의 핵심이라고 알려졌지만, "
            "최근 연구에서는 콘크리트 속 석회 덩어리가 균열을 "
            "스스로 메우는 역할을 했다는 사실도 밝혀졌습니다.\n\n"
            "바닷물과의 광물 반응과 탄산화 작용까지, "
            "로마 콘크리트가 오래 버틴 비밀은 하나가 아니라 "
            "여러 반응의 조합이었습니다.\n\n"
            "#로마 #콘크리트 #판테온 #고대기술 #과학 #세계한입"
        ),

        "tags": [
            "로마 콘크리트",
            "고대 로마",
            "판테온",
            "로마 건축",
            "고대 기술",
            "자가 치유 콘크리트",
            "화산재",
            "석회",
            "건축",
            "과학",
            "역사",
            "세계한입",
        ],

        "pinned_comment": (
            "2천 년 동안 버틴 로마 콘크리트의 기술을 "
            "현대 건축에 적용한다면 건물의 수명은 얼마나 길어질까요?"
        ),
    }


def save_json(
    path: Path,
    data: dict[str, Any],
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


def build_episode_package() -> None:
    EPISODE_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    ASSETS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

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

    print("=" * 64)
    print(" EP028 영상 패키지 생성 완료")
    print("=" * 64)
    print(f"Story:    {STORY_PATH}")
    print(f"Timeline: {TIMELINE_PATH}")
    print(f"Manifest: {MEDIA_MANIFEST_PATH}")
    print(f"YouTube:  {YOUTUBE_PATH}")
    print(f"Assets:   {ASSETS_DIR}")
    print()


def run_factory() -> int:
    if not RUNNER_PATH.exists():
        print(f"[실패] Factory Runner가 없습니다: {RUNNER_PATH}")
        return 1

    command = [
        sys.executable,
        str(RUNNER_PATH),
        "--episode",
        EPISODE_ID,
    ]

    print("=" * 64)
    print(" EP028 Factory 전체 실행")
    print("=" * 64)
    print("실행 명령:")
    print(" ".join(command))
    print()

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        check=False,
    )

    return result.returncode


def print_result(return_code: int) -> None:
    print()
    print("=" * 64)

    if return_code == 0:
        print(" EP028 영상 제작 완료")
        print("=" * 64)
        print(
            "예상 출력:",
            OUTPUT_DIR / f"{EPISODE_ID}.mp4",
        )
        print(
            "유튜브 정보:",
            YOUTUBE_PATH,
        )
    else:
        print(" EP028 Factory 실행 실패")
        print("=" * 64)
        print(
            "위에 표시된 첫 번째 오류를 확인하세요."
        )


def main() -> int:
    build_episode_package()

    return_code = run_factory()
    print_result(return_code)

    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
