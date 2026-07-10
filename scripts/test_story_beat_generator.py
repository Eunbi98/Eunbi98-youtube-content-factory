from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.story_beats import StoryBeatGenerator


EXPECTED_KEYS = [
    "hook",
    "misconception",
    "reveal",
    "explanation",
    "second_reveal",
    "human_moment",
    "ending",
    "next_episode_hook",
    "emotion_curve",
]


def main() -> None:
    fixture_path = PROJECT_ROOT / "episodes" / "episode_001" / "knowledge_pack.json"
    knowledge_pack = json.loads(fixture_path.read_text(encoding="utf-8"))

    generator = StoryBeatGenerator()
    beats = generator.generate(knowledge_pack).to_dict()

    assert list(beats.keys()) == EXPECTED_KEYS
    assert beats["emotion_curve"] == [
        "curiosity",
        "surprise",
        "understanding",
        "wonder",
    ]
    assert beats["hook"] == "사람이 382일 동안 우주에 있으면?"
    assert beats["misconception"] == "사람들은 근육부터 망가질 거라고 생각한다."
    assert beats["reveal"] == "하지만 먼저 문제가 생길 수 있는 곳은 눈이다."
    assert "미세중력" in beats["explanation"]
    assert "시야 변화" in beats["explanation"]
    assert "골밀도" in beats["second_reveal"]
    assert "1~1.5%" in beats["second_reveal"]
    assert beats["human_moment"] == "우주에 적응한 몸은 지구로 돌아온 뒤 다시 적응해야 한다."
    assert beats["ending"] == "인간의 몸은 지구용으로 설계되어 있다는 결론."
    assert beats["next_episode_hook"] == "화성에서는 이 변화가 더 심해질까?"

    verified_facts = "\n".join(knowledge_pack["verified_facts"])
    assert "체액" in verified_facts
    assert "시야" in verified_facts or "시각" in verified_facts
    assert "골밀도" in verified_facts
    assert "근육" in verified_facts

    with TemporaryDirectory() as temp_dir:
        input_path = Path(temp_dir) / "knowledge_pack.json"
        output_path = Path(temp_dir) / "story_beats.json"
        input_path.write_text(
            json.dumps(knowledge_pack, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        result = generator.generate_from_file(input_path, output_path)
        output = json.loads(output_path.read_text(encoding="utf-8"))

        assert result.episode_id == "episode_001"
        assert output["hook"] == beats["hook"]
        assert output["second_reveal"] == beats["second_reveal"]

    print("story_beat_generator_ok")


if __name__ == "__main__":
    main()
