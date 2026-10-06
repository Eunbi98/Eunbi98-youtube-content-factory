from story_compiler import StoryCompiler
from story_graph import (
    Answer,
    Ending,
    Fact,
    Hook,
    Narrative,
    Story,
    StoryMedia,
)
from timeline_schema import (
    Timeline,
    save_timeline,
)


def build_ep008_story() -> Story:
    return Story(
        episode_id="ep008",
        title="사라진 도시는\n어떻게 발견될까?",
        fps=30,
        width=1080,
        height=1920,
        background_color="#000000",
        title_color="#7CFFB2",
        caption_color="#FFFFFF",
        accent_color="#7CFFB2",
        beats=[
            Hook(
                title=(
                    "땅속에 도시 전체가 "
                    "숨겨져 있다면?"
                ),
                narration=(
                    "수백 년 동안 아무도 몰랐던 "
                    "도시가 땅속에서 발견된다면 "
                    "믿으시겠습니까?"
                ),
                subtitle=(
                    "땅속에 도시 전체가\n"
                    "숨겨져 있다면?"
                ),
                duration=5,
                media=StoryMedia(
                    type="image",
                    src=(
                        "assets/ep008/"
                        "scene_001.jpg"
                    ),
                ),
                keywords=[
                    "lost underground city",
                    "ancient ruins mystery",
                ],
            ),
            Answer(
                title=(
                    "실제로 사라진 도시는 "
                    "계속 발견됩니다"
                ),
                narration=(
                    "사막과 밀림, 현대 도시 아래에서도 "
                    "오랫동안 잊힌 유적이 발견되고 "
                    "있습니다."
                ),
                subtitle=(
                    "사라진 도시는 지금도\n"
                    "발견되고 있습니다"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src=(
                        "assets/ep008/"
                        "scene_002.jpg"
                    ),
                ),
                keywords=[
                    "archaeological discovery",
                    "buried ancient city",
                ],
            ),
            Narrative(
                title=(
                    "흙과 식물이 모든 흔적을 "
                    "감춰 버립니다"
                ),
                narration=(
                    "도시가 버려진 뒤 오랜 시간이 "
                    "지나면 건물은 무너지고 흙과 "
                    "식물이 그 위를 덮습니다."
                ),
                subtitle=(
                    "시간이 도시의 흔적을\n"
                    "완전히 덮어 버립니다"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src=(
                        "assets/ep008/"
                        "scene_003.jpg"
                    ),
                ),
                keywords=[
                    "ruins covered by jungle",
                    "lost city landscape",
                ],
            ),
            Fact(
                title=(
                    "레이저는 숲 아래까지 "
                    "볼 수 있습니다"
                ),
                narration=(
                    "최근에는 라이다라는 레이저 기술로 "
                    "울창한 숲 아래 숨겨진 건물과 "
                    "도로의 형태까지 찾아냅니다."
                ),
                subtitle=(
                    "레이저로 숲 아래의\n"
                    "도시를 찾아냅니다"
                ),
                duration=8,
                media=StoryMedia(
                    type="image",
                    src=(
                        "assets/ep008/"
                        "scene_004.jpg"
                    ),
                ),
                keywords=[
                    "lidar archaeology",
                    "jungle city scan",
                ],
            ),
            Ending(
                title=(
                    "아직 발견되지 않은 도시가 "
                    "남아 있을지도 모릅니다"
                ),
                narration=(
                    "우리가 걷는 땅 아래에도 아직 "
                    "발견되지 않은 역사가 숨어 있을지 "
                    "모릅니다."
                ),
                subtitle=(
                    "우리 발밑에도 사라진\n"
                    "도시가 있을까요?"
                ),
                duration=6,
                media=StoryMedia(
                    type="image",
                    src=(
                        "assets/ep008/"
                        "scene_005.jpg"
                    ),
                ),
                keywords=[
                    "hidden history",
                    "undiscovered ancient city",
                ],
            ),
        ],
    )


def build_ep008() -> Timeline:
    story = build_ep008_story()

    compiler = StoryCompiler()

    return compiler.compile(story)


if __name__ == "__main__":
    timeline = build_ep008()

    output_path = (
        "projects/episodes/ep008/"
        "timeline.json"
    )

    save_timeline(
        timeline,
        output_path,
    )

    print(
        "EP008 Story Compiler 실행 완료"
    )
    print(
        f"Scene 수: {len(timeline.scenes)}"
    )
    print(
        f"전체 길이: {timeline.duration}초"
    )
    print(
        f"출력 경로: {output_path}"
    )