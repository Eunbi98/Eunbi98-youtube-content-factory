from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.media import MediaSelector


REQUIRED_KEYS = {
    "scene",
    "narration",
    "media_type",
    "preferred_source",
    "source_confidence",
    "reason",
    "search_queries",
    "fallback_media_type",
    "visual_note",
    "copyright_note",
}

VALID_MEDIA_TYPES = {
    "real_video",
    "real_image",
    "official_image",
    "animation",
    "infographic",
    "ai_image",
}

VALID_SOURCES = {
    "NASA",
    "ESA",
    "Wikipedia",
    "Generated",
    "Stock",
}

REAL_FIRST_TYPES = {
    "real_video",
    "real_image",
    "official_image",
}


def main() -> None:
    episode_dir = PROJECT_ROOT / "episodes" / "episode_001"
    output_json = episode_dir / "media_plan.json"
    output_md = episode_dir / "media_plan.md"

    plan = MediaSelector().generate_from_files(
        script_path=episode_dir / "script.json",
        visual_plan_path=episode_dir / "visual_plan.json",
        knowledge_pack_path=episode_dir / "knowledge_pack.json",
        output_dir=episode_dir,
    )

    assert output_json.exists()
    assert output_md.exists()
    saved_plan = json.loads(output_json.read_text(encoding="utf-8"))
    script = json.loads((episode_dir / "script.json").read_text(encoding="utf-8"))

    assert saved_plan == plan
    assert len(plan) == len(script["narration_lines"])

    for index, item in enumerate(plan, start=1):
        assert REQUIRED_KEYS.issubset(item)
        assert item["scene"] == index
        assert item["narration"] == script["narration_lines"][index - 1]
        assert item["media_type"] in VALID_MEDIA_TYPES
        assert item["preferred_source"] in VALID_SOURCES
        assert 1 <= item["source_confidence"] <= 5
        assert item["fallback_media_type"] == "ai_image"
        assert item["search_queries"]
        assert item["copyright_note"] == "공식 공개 자료 우선, 사용 조건 확인 필요"

    confidence_by_source = {
        "NASA": 5,
        "ESA": 5,
        "Wikipedia": 3,
        "Stock": 3,
        "Generated": 2,
    }
    for item in plan:
        assert item["source_confidence"] == confidence_by_source[item["preferred_source"]]

    real_public_count = sum(item["media_type"] in REAL_FIRST_TYPES for item in plan)
    ai_count = sum(item["media_type"] == "ai_image" for item in plan)
    assert real_public_count / len(plan) >= 0.5
    assert ai_count / len(plan) <= 0.25

    astronaut_items = [
        item
        for item in plan
        if any(keyword in item["narration"] for keyword in ("우주비행사", "운동", "돌아오면", "걷는"))
    ]
    assert astronaut_items
    assert all(item["media_type"] == "real_video" for item in astronaut_items)
    assert all(item["preferred_source"] in ("NASA", "ESA") for item in astronaut_items)
    assert all(item["media_type"] != "ai_image" for item in astronaut_items)

    explainer_items = [
        item
        for item in plan
        if any(keyword in item["narration"] for keyword in ("체액", "시야", "골밀도", "뼈", "근육"))
    ]
    assert explainer_items
    assert all(item["media_type"] in ("animation", "infographic") for item in explainer_items)

    mars_item = plan[-1]
    assert "화성" in mars_item["narration"]
    assert mars_item["media_type"] in ("ai_image", "official_image")

    print("media_selector_ok")
    print(f"real_public_ratio={real_public_count / len(plan):.2f}")
    print(f"ai_image_ratio={ai_count / len(plan):.2f}")


if __name__ == "__main__":
    main()
