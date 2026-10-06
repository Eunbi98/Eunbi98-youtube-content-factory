from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DIRECTOR_DIR = ROOT_DIR / "projects" / "director"

if str(DIRECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(DIRECTOR_DIR))

from factory_core import FactoryCore
from story_graph import (
    Answer,
    Ending,
    Fact,
    Hook,
    Narrative,
    Story,
    StoryMedia,
)
from timeline_schema import save_timeline


EPISODE_ID = "ep025"

OUTPUT_PATH = (
    ROOT_DIR
    / "projects"
    / "episodes"
    / EPISODE_ID
    / "timeline.json"
)


def build_ep025_story() -> Story:
    return Story(
        episode_id=EPISODE_ID,
        title="사하라 사막 아래에\n거대한 강이 있었다?",
        fps=30,
        width=1080,
        height=1920,
        background_color="#17212D",
        title_color="#7BFEB4",
        caption_color="#FFFFFF",
        accent_color="#7BFEB4",
        beats=[
            Hook(
                title="사하라 사막 아래에\n거대한 강이 있었다?",
                narration=(
                    "지금은 끝없는 사막인 사하라 아래에 "
                    "거대한 강이 있었다는 사실, 알고 계셨나요?"
                ),
                subtitle=(
                    "지금은 끝없는 사막인 사하라 아래에 "
                    "거대한 강이 있었다는 사실, 알고 계셨나요?"
                ),
                duration=8,
                media=StoryMedia(
                    type="image",
                    src="scene_001.jpg",
                ),
                keywords=[
                    "Sahara Desert aerial sand dunes",
                    "Sahara desert satellite view",
                    "Sahara desert drone landscape",
                ],
            ),
            Answer(
                title="모래 아래에서 발견된\n고대 강의 흔적",
                narration=(
                    "과학자들은 위성 레이더를 이용해 "
                    "모래 아래 숨겨진 거대한 강의 흔적을 발견했습니다."
                ),
                subtitle=(
                    "과학자들은 위성 레이더를 이용해 "
                    "모래 아래 숨겨진 거대한 강의 흔적을 발견했습니다."
                ),
                duration=9,
                media=StoryMedia(
                    type="image",
                    src="scene_002.jpg",
                ),
		keywords=[
 		   "Sahara desert satellite map",
		    "Sahara satellite image",
		    "Sahara desert map",
		],
            ),
            Narrative(
                title="사하라는 한때\n푸른 초원이었습니다",
                narration=(
                    "약 오천 년에서 만 년 전, 지금의 사하라는 "
                    "초원과 강이 흐르는 풍요로운 땅이었습니다."
                ),
                subtitle=(
                    "약 오천 년에서 만 년 전, 지금의 사하라는 "
                    "초원과 강이 흐르는 풍요로운 땅이었습니다."
                ),
                duration=9,
                media=StoryMedia(
                    type="image",
                    src="scene_003.jpg",
                ),
                keywords=[
                    "Green Sahara reconstruction",
                    "ancient Sahara grassland lake",
                    "African humid period landscape",
                ],
            ),
            Fact(
                title="강은 인류의\n이동 통로였습니다",
                narration=(
                    "이 강은 초기 인류가 이동하고 정착하는 "
                    "중요한 길이었을 것으로 추정되고 있습니다."
                ),
                subtitle=(
                    "이 강은 초기 인류가 이동하고 정착하는 "
                    "중요한 길이었을 것으로 추정되고 있습니다."
                ),
                duration=9,
                media=StoryMedia(
                    type="image",
                    src="scene_004.jpg",
                ),
                keywords=[
                    "ancient human migration North Africa",
                    "prehistoric people Sahara river",
                    "early humans African landscape",
                ],
            ),
            Ending(
                title="사막 아래에는 아직도\n과거가 숨어 있습니다",
                narration=(
                    "오늘도 사하라의 모래 아래에는 우리가 아직 발견하지 못한 "
                    "과거의 흔적이 숨어 있을지 모릅니다."
                ),
                subtitle=(
                    "오늘도 사하라의 모래 아래에는 우리가 아직 발견하지 못한 "
                    "과거의 흔적이 숨어 있을지 모릅니다."
                ),
                duration=10,
                media=StoryMedia(
                    type="image",
                    src="scene_005.jpg",
                ),
                keywords=[
                    "Sahara Desert ancient landscape comparison",
                    "Sahara desert aerial sunset",
                    "hidden history beneath desert",
                ],
            ),
        ],
    )


def main() -> int:
    story = build_ep025_story()

    result = FactoryCore().build_with_result(story)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    save_timeline(
        result.timeline,
        str(OUTPUT_PATH),
    )

    if not OUTPUT_PATH.exists():
        raise RuntimeError(
            f"Timeline 저장 실패: {OUTPUT_PATH}"
        )

    print("=" * 60)
    print("EP025 Timeline 생성 완료")
    print("=" * 60)
    print(f"에피소드: {story.episode_id}")
    print(f"제목: {story.title}")
    print(f"장면 수: {len(result.timeline.scenes)}")
    print(f"전체 길이: {result.timeline.duration}초")
    print(f"저장 위치: {OUTPUT_PATH}")
    print("=" * 60)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


