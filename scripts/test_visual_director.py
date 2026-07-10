from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.visual_director import VisualDirector


REQUIRED_KEYS = {
    "scene",
    "narration",
    "visual_type",
    "reason",
    "search_keywords",
    "image_prompt",
    "camera_motion",
    "duration",
}

VALID_VISUAL_TYPES = {
    "real_video",
    "real_image",
    "ai_image",
    "animation",
    "infographic",
}

VALID_CAMERA_MOTIONS = {
    "zoom_in",
    "zoom_out",
    "pan_left",
    "pan_right",
    "none",
}


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    script_path = episode_dir / "script.json"
    output_path = episode_dir / "visual_plan.json"

    plan = VisualDirector().generate_from_file(script_path, output_path)
    script_data = json.loads(script_path.read_text(encoding="utf-8"))
    saved_plan = json.loads(output_path.read_text(encoding="utf-8"))

    assert output_path.exists()
    assert plan == saved_plan
    assert len(plan) == len(script_data["narration_lines"])

    for index, item in enumerate(plan, start=1):
        assert REQUIRED_KEYS.issubset(item)
        assert item["scene"] == index
        assert item["narration"] == script_data["narration_lines"][index - 1]
        assert item["visual_type"] in VALID_VISUAL_TYPES
        assert item["camera_motion"] in VALID_CAMERA_MOTIONS
        assert isinstance(item["search_keywords"], list)
        assert item["search_keywords"]
        assert item["duration"] > 0

        if item["visual_type"] in ("real_video", "real_image"):
            assert item["image_prompt"] == ""

    number_scenes = [
        item
        for item in plan
        if any(token in item["narration"] for token in ("382일", "1~1.5%", "2시간"))
    ]
    assert number_scenes
    assert all(item["visual_type"] == "infographic" for item in number_scenes)

    astronaut_scenes = [
        item
        for item in plan
        if "우주비행사" in item["narration"] or "운동" in item["narration"]
    ]
    assert astronaut_scenes
    assert all(item["visual_type"] != "ai_image" for item in astronaut_scenes)

    explanation_scenes = [
        item
        for item in plan
        if "체액" in item["narration"] or "눈" in item["narration"]
    ]
    assert explanation_scenes
    assert any(item["visual_type"] == "animation" for item in explanation_scenes)

    emotional_scene = plan[-1]
    assert "화성" in emotional_scene["narration"]
    assert emotional_scene["visual_type"] == "ai_image"
    assert emotional_scene["image_prompt"]

    print("visual_director_ok")


if __name__ == "__main__":
    main()
