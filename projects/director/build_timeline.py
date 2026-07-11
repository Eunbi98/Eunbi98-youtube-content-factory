from timeline_schema import (
    Media,
    Scene,
    Timeline,
    TimelineTheme,
    save_timeline,
)


def build_ep007() -> Timeline:
    scenes = [
        Scene(
            id="scene_001",
            type="hook",
            start=0,
            duration=5,
            title="사람은 왜 과거를 파헤칠까?",
            narration=(
                "우리는 왜 오래된 유적과 "
                "기록에 끌릴까요?"
            ),
            subtitle=(
                "왜 과거를\n"
                "파헤칠까?"
            ),
            media=Media(
                type="image",
                src="assets/ep007/scene_001.jpg",
            ),
            keywords=[
                "ancient ruins",
                "history mystery",
            ],
            background_color="#14202B",
        ),
        Scene(
            id="scene_002",
            type="answer",
            start=5,
            duration=7,
            title="답은 단순한 호기심이 아닙니다",
            narration=(
                "과거를 아는 건 지금의 우리를 "
                "이해하는 가장 빠른 방법이기 "
                "때문입니다."
            ),
            subtitle=(
                "지금의 우리를 알기\n"
                "위해서입니다"
            ),
            media=Media(
                type="image",
                src="assets/ep007/scene_002.jpg",
            ),
            keywords=[
                "archive",
                "old documents",
            ],
            background_color="#223748",
        ),
        Scene(
            id="scene_003",
            type="story",
            start=12,
            duration=8,
            title="작은 흔적이 역사를 바꿉니다",
            narration=(
                "때로는 깨진 도자기 조각 하나가 "
                "사라진 시대의 생활을 "
                "보여주기도 합니다."
            ),
            subtitle=(
                "작은 조각 하나가\n"
                "역사를 바꿉니다"
            ),
            media=Media(
                type="image",
                src="assets/ep007/scene_003.jpg",
            ),
            keywords=[
                "pottery fragment",
                "archaeology",
            ],
            background_color="#314A5D",
        ),
        Scene(
            id="scene_004",
            type="fact",
            start=20,
            duration=8,
            title="기술은 과거를 다시 보이게 합니다",
            narration=(
                "이제는 인공지능과 3D 스캔으로 "
                "훼손된 문화유산도 다시 "
                "복원해 볼 수 있습니다."
            ),
            subtitle=(
                "AI와 3D가\n"
                "과거를 복원합니다"
            ),
            media=Media(
                type="image",
                src="assets/ep007/scene_004.jpg",
            ),
            keywords=[
                "3d scan heritage",
                "ai restoration",
            ],
            background_color="#1C3040",
        ),
        Scene(
            id="scene_005",
            type="ending",
            start=28,
            duration=6,
            title="과거는 끝난 이야기가 아닙니다",
            narration=(
                "당신은 어떤 사라진 역사를 "
                "다시 보고 싶나요?"
            ),
            subtitle=(
                "어떤 역사를\n"
                "다시 보고 싶나요?"
            ),
            media=Media(
                type="image",
                src="assets/ep007/scene_005.jpg",
            ),
            keywords=[
                "museum",
                "heritage future",
            ],
            background_color="#101820",
        ),
    ]

    return Timeline(
        version="5.1",
        episode_id="ep007",
        title="과거는 왜\n다시 발견될까?",
        fps=30,
        width=1080,
        height=1920,
        duration=34,
        bgm=None,
        voice=None,
        theme=TimelineTheme(
            background_color="#000000",
            title_color="#7CFFB2",
            caption_color="#FFFFFF",
            accent_color="#7CFFB2",
        ),
        scenes=scenes,
    )


if __name__ == "__main__":
    timeline = build_ep007()

    output_path = (
        "projects/episodes/ep007/"
        "timeline.json"
    )

    save_timeline(
        timeline,
        output_path,
    )

    print(
        "EP007 timeline.json 생성 완료"
    )
    print(
        f"출력 경로: {output_path}"
    )