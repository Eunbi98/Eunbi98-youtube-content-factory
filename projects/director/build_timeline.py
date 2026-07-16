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

def build_ep010_story() -> Story:
    return Story(
        episode_id="ep010",
        title="이 숲의 나무들은\n왜 모두 휘어 있을까?",
        fps=30,
        width=1080,
        height=1920,
        background_color="#000000",
        title_color="#7CFFB2",
        caption_color="#FFFFFF",
        accent_color="#7CFFB2",
        beats=[
            Hook(
                title="왜 이 나무들은\n모두 휘어 있을까요?",
                narration=(
                    "왜 이 숲의 나무들은 모두 같은 방향으로 "
                    "휘어 있을까요?"
                ),
                subtitle=(
                    "왜 이 숲의 나무들은\n"
                    "모두 휘어 있을까요?"
                ),
                duration=5,
                media=StoryMedia(
                    type="image",
                    src="ep010/scene_001.jpg",
                ),
                keywords=[
                    "Crooked Forest Poland",
                    "Krzywy Las curved pine trees",
                    "crooked forest wide view",
                ],
            ),
            Answer(
                title="폴란드의\n휘어진 숲",
                narration=(
                    "이곳은 폴란드의 휘어진 숲입니다. "
                    "약 사백 그루의 소나무가 비슷한 모양으로 "
                    "휘어 있습니다."
                ),
                subtitle=(
                    "약 400그루의 소나무가\n"
                    "비슷하게 휘어 있습니다"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src="ep010/scene_002.jpg",
                ),
                keywords=[
                    "Crooked Forest Gryfino Poland",
                    "Krzywy Las pine trees",
                    "curved pine trees Poland close up",
                ],
            ),
            Narrative(
                title="사람이 일부러\n구부렸을까?",
                narration=(
                    "가장 유명한 가설은 사람이 곡선 목재를 얻기 위해 "
                    "어린 나무를 일부러 구부렸다는 것입니다."
                ),
                subtitle=(
                    "곡선 목재를 얻으려고\n"
                    "사람이 구부렸다는 가설"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src="ep010/scene_003.jpg",
                ),
                keywords=[
                    "Crooked Forest bent tree trunks",
                    "curved pine trunk Poland",
                    "Krzywy Las tree detail",
                ],
            ),
            Fact(
                title="다른 가설도 있지만\n증거는 없습니다",
                narration=(
                    "폭설과 강한 바람, 전쟁 당시 차량 때문이라는 "
                    "주장도 있지만 확실한 증거는 없습니다."
                ),
                subtitle=(
                    "폭설과 전쟁 때문이라는\n"
                    "주장도 있습니다"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src="ep010/scene_004.jpg",
                ),
                keywords=[
                    "Crooked Forest winter Poland",
                    "Krzywy Las forest landscape",
                    "crooked pine forest snow",
                ],
            ),
            Ending(
                title="아직 풀리지 않은\n숲의 미스터리",
                narration=(
                    "정확한 원인은 아직 밝혀지지 않았습니다. "
                    "여러분은 사람이 만든 숲이라고 생각하시나요, "
                    "자연이 만든 현상이라고 생각하시나요?"
                ),
                subtitle=(
                    "사람이 만든 숲일까요?\n"
                    "자연이 만든 현상일까요?"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src="ep010/scene_005.jpg",
                ),
                keywords=[
                    "Crooked Forest Poland mysterious",
                    "Krzywy Las forest wide",
                    "crooked pine trees cinematic",
                ],
            ),
        ],
    )

def build_ep011_story() -> Story:
    return Story(
        episode_id="ep011",
        title="\uc7a0\ub4e4 \ub54c \uac11\uc790\uae30\n\ub5a8\uc5b4\uc9c0\ub294 \ub290\ub08c\uc758 \uc774\uc720",
        fps=30,
        width=1080,
        height=1920,
        background_color="#000000",
        title_color="#7CFFB2",
        caption_color="#FFFFFF",
        accent_color="#7CFFB2",
        beats=[
            Hook(
                title="\uc65c \uc7a0\ub4e4 \ub54c\n\ub5a8\uc5b4\uc9c0\ub294 \ub290\ub08c\uc774 \ub4e4\uae4c\uc694?",
                narration=(
                    "\uc65c \uc7a0\ub4e4 \ub54c \uac11\uc790\uae30 "
                    "\ub5a8\uc5b4\uc9c0\ub294 \ub290\ub08c\uc774 \ub4e4\uae4c\uc694?"
                ),
                subtitle=(
                    "\uc65c \uc7a0\ub4e4 \ub54c \uac11\uc790\uae30\n"
                    "\ub5a8\uc5b4\uc9c0\ub294 \ub290\ub08c\uc774 \ub4e4\uae4c\uc694?"
                ),
                duration=5,
                media=StoryMedia(
                    type="image",
                    src="ep011/scene_001.jpg",
                ),
                keywords=[
                    "sleeping",
                    "sleep",
                    "bed",
                ],
            ),
            Answer(
                title="\ubab8\uc774 \uc6c0\ucc14\ud558\uba70\n\uae68\ub294 \uc21c\uac04",
                narration=(
                    "\uc7a0\ub4e4\uae30 \uc9c1\uc804 \ubab8\uc774 \uc6c0\ucc14\ud558\uba70 "
                    "\uae6c \uc801\uc774 \uc788\ub2e4\uba74 \uc5ec\ub7ec\ubd84\ub9cc "
                    "\uadf8\ub7f0 \uac83\uc774 \uc544\ub2d9\ub2c8\ub2e4."
                ),
                subtitle=(
                    "\ubab8\uc774 \uc6c0\ucc14\ud558\uba70 \uae7c\ub2e4\uba74\n"
                    "\uc5ec\ub7ec\ubd84\ub9cc \uadf8\ub7f0 \uac8c \uc544\ub2d9\ub2c8\ub2e4"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src="ep011/scene_002.jpg",
                ),
                keywords=[
                    "waking up",
                    "waking up in bed",
                    "startled awake",   
                ],
            ),
            Narrative(
                title="\ub1cc\uac00 \ucd94\ub77d\uc73c\ub85c\n\ucc29\uac01\ud569\ub2c8\ub2e4",
                narration=(
                    "\uc7a0\uc774 \ub4e4\uba74\uc11c \uadfc\uc721\uc758 \ud798\uc774 "
                    "\ud480\ub9ac\ub294 \uc21c\uac04, \ub1cc\uac00 \uadf8 \ubcc0\ud654\ub97c "
                    "\ucd94\ub77d\uc73c\ub85c \ucc29\uac01\ud558\uae30\ub3c4 \ud569\ub2c8\ub2e4."
                ),
                subtitle=(
                    "\uadfc\uc721\uc758 \ud798\uc774 \ud480\ub9ac\ub294 \uc21c\uac04\n"
                    "\ub1cc\uac00 \ucd94\ub77d\uc73c\ub85c \ucc29\uac01\ud569\ub2c8\ub2e4"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src="ep011/scene_003.jpg",
                ),
                keywords=[
                    "human brain illustration",
                    "brain neurons",
                    "brain activity",
                ],
            ),
            Fact(
                title="\uc774 \ud604\uc0c1\uc758 \uc774\ub984\uc740\n\uc785\uba74\uacbd\ub828",
                narration=(
                    "\uc774 \ud604\uc0c1\uc744 \uc785\uba74\uacbd\ub828\uc774\ub77c\uace0 "
                    "\ud558\uba70, \ub300\ubd80\ubd84 \uac74\uac15\ud55c \uc0ac\ub78c\uc5d0\uac8c\ub3c4 "
                    "\ub098\ud0c0\ub0a0 \uc218 \uc788\uc2b5\ub2c8\ub2e4."
                ),
                subtitle=(
                    "\uc774 \ud604\uc0c1\uc758 \uc774\ub984\uc740 \uc785\uba74\uacbd\ub828\n"
                    "\ub300\ubd80\ubd84 \uc815\uc0c1\uc801\uc778 \ud604\uc0c1\uc785\ub2c8\ub2e4"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src="ep011/scene_004.jpg",
                ),
                keywords=[
                    "sleep illustration",
                    "sleep science",
                    "sleeping body",
                ],
            ),
            Ending(
                title="\ud53c\uace4\ud560\uc218\ub85d\n\ub354 \uc790\uc8fc \uc0dd\uae38 \uc218 \uc788\uc2b5\ub2c8\ub2e4",
                narration=(
                    "\ud53c\uace4\ud558\uac70\ub098 \uc2a4\ud2b8\ub808\uc2a4\ub97c "
                    "\ub9ce\uc774 \ubc1b\uc73c\uba74 \ub354 \uc790\uc8fc \ub098\ud0c0\ub0a0 "
                    "\uc218 \uc788\uc2b5\ub2c8\ub2e4. \uc5ec\ub7ec\ubd84\ub3c4 "
                    "\uc774\ub7f0 \uacbd\ud5d8\uc774 \uc788\uc5c8\ub098\uc694?"
                ),
                subtitle=(
                    "\ud53c\uace4\ud558\uba74 \ub354 \uc790\uc8fc \uc0dd\uae38 \uc218 \uc788\uc2b5\ub2c8\ub2e4\n"
                    "\uc5ec\ub7ec\ubd84\ub3c4 \uacbd\ud5d8\ud574 \ubcf4\uc168\ub098\uc694?"
                ),
                duration=7,
                media=StoryMedia(
                    type="image",
                    src="ep011/scene_005.jpg",
                ),
                keywords=[
                    "tired person",
                    "stressed person",
                    "peaceful sleeping",
                ],
            ),
        ],
    )

