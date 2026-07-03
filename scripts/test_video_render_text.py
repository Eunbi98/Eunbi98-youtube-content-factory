from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.story import ScriptQAEngine, normalize_english_terms
from app.video.caption_layout import layout_caption_text
from app.video.caption_timing import build_caption_schedule, fit_caption_texts_to_duration
from app.video.style_config import DEFAULT_VIDEO_STYLE
from app.video.title_generator import VideoTitleGenerator


def main() -> None:
    qa = ScriptQAEngine()
    title_generator = VideoTitleGenerator()
    raw_script = (
        "NASA James Webb Space Telescope가 FS Tau 주변에서 이상한 신호를 포착했습니다.\n"
        "Nasa James Webb Space 관측 자료에는 알 수 없는 대기 변화가 있었다.\n"
        "마지막 문장은 반드시 자막에 표시되어야 합니다."
    )
    script = qa.polish_script(raw_script)
    article = SimpleNamespace(
        title="NASA's Webb Telescope Spots Mysterious FS Tau Signal",
        thumbnail="NASA James Webb Space mystery",
        script=script,
        scenes=[
            {
                "order": index,
                "text": line,
                "image_keyword": "space telescope",
                "duration": 4,
            }
            for index, line in enumerate(script.splitlines(), start=1)
        ],
        source="NASA",
    )

    caption_config = DEFAULT_VIDEO_STYLE["caption"]
    caption_background_enabled = caption_config.get(
        "caption_background_enabled",
        False,
    )

    if caption_background_enabled:
        raise AssertionError("Caption background must be disabled.")

    script_lines = [
        line.strip()
        for line in script.splitlines()
        if line.strip()
    ]
    scene_lines = [
        scene["text"]
        for scene in article.scenes
    ]
    simulated_video_duration = 12.0
    fitted_scene_lines = fit_caption_texts_to_duration(
        scene_lines,
        duration=simulated_video_duration,
        min_seconds=caption_config.get("min_seconds", 1.5),
    )
    caption_schedule = build_caption_schedule(
        text_count=len(fitted_scene_lines),
        total_duration=simulated_video_duration,
        default_seconds=caption_config.get("seconds", 4),
        min_seconds=caption_config.get("min_seconds", 1.5),
    )
    last_caption_start, last_caption_duration = caption_schedule[-1]
    last_caption_end = last_caption_start + last_caption_duration
    silent_visual_tail_duration = max(0.0, simulated_video_duration - last_caption_end)

    if abs(simulated_video_duration - last_caption_end) > 0.2:
        raise AssertionError(
            "Last caption must end with the video: "
            f"video={simulated_video_duration}, caption_end={last_caption_end}"
        )

    one_line_sample = "알 수 없는 대기 신호를 포착했다."
    one_line_wrapped = layout_caption_text(
        one_line_sample,
        one_line_max=caption_config.get("line_length", 28),
    )

    if "\n" in one_line_wrapped:
        raise AssertionError(
            f"One-line caption should not wrap: {one_line_wrapped}"
        )

    caption_samples = [
        "제임스 웹 우주망원경이 먼 행성 주변에서 이상한 신호를 포착했습니다.",
        "전문가들은 안전 기준도 필요하다고 말했다.",
        "다음 관측 결과에 따라 해석이 달라질 수 있다.",
    ]
    caption_layouts = []

    for sample in caption_samples:
        wrapped = layout_caption_text(
            sample,
            one_line_max=caption_config.get("line_length", 28),
            two_line_max=caption_config.get("max_length", 56),
        )
        lines = wrapped.splitlines()

        if len(lines) > 2:
            raise AssertionError(f"Caption has too many lines: {wrapped}")

        if len(sample) <= caption_config.get("line_length", 28) and len(lines) != 1:
            raise AssertionError(f"One-line possible caption wrapped: {wrapped}")

        if "필요하다고\n말했다" in wrapped:
            raise AssertionError(f"Protected phrase split: {wrapped}")

        caption_layouts.append({
            "input": sample,
            "wrapped": wrapped,
            "line_count": len(lines),
        })

    result = {
        "final_title": title_generator.generate(article),
        "caption_background_enabled": caption_background_enabled,
        "script_line_count": len(script_lines),
        "scene_count": len(scene_lines),
        "last_script_line": script_lines[-1],
        "last_scene_text": scene_lines[-1],
        "fitted_last_scene_text": fitted_scene_lines[-1],
        "video_duration": simulated_video_duration,
        "last_caption_end": last_caption_end,
        "last_caption_text": fitted_scene_lines[-1],
        "silent_visual_tail_duration": silent_visual_tail_duration,
        "one_line_sample": {
            "input": one_line_sample,
            "wrapped": one_line_wrapped,
            "line_count": len(one_line_wrapped.splitlines()),
        },
        "caption_layouts": caption_layouts,
        "normalized_terms": normalize_english_terms(raw_script),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
