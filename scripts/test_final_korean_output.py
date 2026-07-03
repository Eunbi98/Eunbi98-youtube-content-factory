from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.content_planner_service import ContentPlannerService
from app.services.final_output_guard import FinalOutputGuard
from app.story import KoreanLanguageGuard


class EnglishFakeLLM:
    def generate(self, prompt: str) -> str:
        return json.dumps(
            {
                "score": 85,
                "summary": "The 10th president spoke at JPL on Jan about a telescope discovery.",
                "script": [
                    "The 10th president spoke at JPL on Jan.",
                    "NASA James Webb Space Telescope found a signal.",
                    "Scientists are watching FS Tau closely.",
                ],
                "scenes": [
                    {
                        "order": 1,
                        "text": "The 10th president spoke at JPL on Jan.",
                        "image_keyword": "NASA JPL",
                        "duration": 4,
                    }
                ],
                "thumbnail_text": "NASA James Webb Space",
                "hashtags": ["#news", "#shorts"],
            },
            ensure_ascii=False,
        )


def main() -> None:
    article = SimpleNamespace(
        title="NASA's James Webb Space Telescope Captures FS Tau",
        source="NASA",
        link="https://example.com/nasa-webb-fs-tau",
        summary="",
        cleaned_content=(
            "NASA's James Webb Space Telescope captured a new view of FS Tau. "
            "The article says scientists are studying the object because it may "
            "show clues about star formation."
        ),
        content="",
        script="",
        scenes=[],
        thumbnail="",
    )

    planner = ContentPlannerService(llm=EnglishFakeLLM())
    plan_result = planner.plan(article)

    article.script = plan_result["script"]
    article.scenes = plan_result["scenes"]
    article.thumbnail = plan_result.get("thumbnail_text", "")

    guard = FinalOutputGuard()
    diagnostics = guard.enforce_article(article)
    language_guard = KoreanLanguageGuard()
    metrics = language_guard.inspect(article.script)

    if not metrics["is_korean_safe"]:
        raise AssertionError(
            f"Final script is not Korean-safe: {metrics}"
        )

    for scene in article.scenes:
        scene_metrics = language_guard.inspect(scene["text"])

        if not scene_metrics["is_korean_safe"]:
            raise AssertionError(
                f"Scene text is not Korean-safe: {scene_metrics}"
            )

    result = {
        "final_title": diagnostics["final_title"],
        "final_script": article.script,
        "final_tts_input": article.script,
        "scene_count": len(article.scenes),
        "last_scene_text": article.scenes[-1]["text"],
        "korean_ratio": round(metrics["korean_ratio"], 3),
        "english_ratio": round(metrics["english_ratio"], 3),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
