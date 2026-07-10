from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.video.caption_layout import CaptionDirector, layout_caption_text


PARTICLES = (
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "에서",
    "로",
    "으로",
    "와",
    "과",
    "도",
    "만",
    "부터",
    "까지",
)


def main() -> None:
    config_path = PROJECT_ROOT / "caption_layout.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))

    assert config["name"] == "caption_director_v1"
    assert config["max_lines"] == 2
    assert config["preferred_line_min"] == 14
    assert config["preferred_line_max"] == 18

    one_line = layout_caption_text("사람이 382일 동안 우주에 있으면?")
    assert one_line == "사람이 382일 동안 우주에 있으면?"

    long_caption = layout_caption_text(
        "미세중력 때문에 체액이 머리 쪽으로 이동하고 시야 변화와 연결될 수 있다"
    )
    long_lines = long_caption.splitlines()
    assert 1 <= len(long_lines) <= 2
    assert len(long_lines) == 2
    assert len(long_lines[1]) >= config["min_second_line"]
    assert "체액" in long_caption
    assert "시야 변화" in long_caption

    number_caption = layout_caption_text(
        "골밀도는 월 1~1.5% 손실될 수 있고 371일 기록과 비교된다"
    )
    assert "1~1.5%" in number_caption
    assert "371일" in number_caption
    assert "1~\n1.5%" not in number_caption
    assert "371\n일" not in number_caption

    english_caption = layout_caption_text(
        "NASA Human Research Program 자료는 Scott Kelly 사례를 함께 본다"
    )
    assert "NASA\nHuman" not in english_caption
    assert "Human\nResearch" not in english_caption
    assert "Research\nProgram" not in english_caption
    assert "Scott\nKelly" not in english_caption

    no_space_caption = CaptionDirector().layout("사람들은근육부터망가질거라고생각한다")
    no_space_lines = no_space_caption.splitlines()
    assert len(no_space_lines) <= 2
    if len(no_space_lines) == 2:
        assert not no_space_lines[1].startswith(PARTICLES)
        assert len(no_space_lines[1]) >= config["min_second_line"]

    breathing_caption = layout_caption_text(
        "우주에 적응한 몸은 지구로 돌아온 뒤 다시 적응해야 한다"
    )
    assert len(breathing_caption.splitlines()) <= 2
    assert not breathing_caption.endswith("\n한다")

    print("caption_director_ok")


if __name__ == "__main__":
    main()
