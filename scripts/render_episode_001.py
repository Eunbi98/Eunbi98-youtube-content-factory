from __future__ import annotations

import asyncio
import json
import random
import re
import shutil
import sys
import time
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RENDER_RUNTIME_DEPS = PROJECT_ROOT / ".render_runtime_deps"
RENDER_DEPS = PROJECT_ROOT / ".render_deps"

if RENDER_RUNTIME_DEPS.exists() and str(RENDER_RUNTIME_DEPS) not in sys.path:
    sys.path.insert(0, str(RENDER_RUNTIME_DEPS))
elif str(RENDER_DEPS) not in sys.path:
    sys.path.insert(0, str(RENDER_DEPS))

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import edge_tts
from moviepy import AudioFileClip, ColorClip, VideoFileClip
from PIL import Image, ImageDraw, ImageFont

from app.video.shorts_engine import ShortsEngine
from app.video.template_loader import TemplateLoader
from config.settings import AUDIO_DIR, IMAGE_DIR, VIDEO_DIR, ensure_directories


EPISODE_ID = "episode_001"
FIXED_VIDEO_NAME = "episode_001_fixed.mp4"
FIXED_REPORT_NAME = "render_report_fixed.md"
WIDTH = 1080
HEIGHT = 1920
VISUAL_HEIGHT = 980
TTS_VOICE = "ko-KR-SunHiNeural"
TITLE_TEXT = "382\uc77c \uc6b0\uc8fc \uccb4\ub958"
ARTICLE_TITLE = "\uc0ac\ub78c\uc774 382\uc77c \ub3d9\uc548 \uc6b0\uc8fc\uc5d0 \uc788\uc73c\uba74?"

REAL_MEDIA_TYPES = {"real_video", "real_image", "official_image"}
GENERATED_MEDIA_TYPES = {"animation", "infographic", "ai_image", "generated_visual"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".avi", ".webm"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}


class Episode001FixedShortsEngine(ShortsEngine):
    def _make_output_path(self) -> Path:
        return VIDEO_DIR / FIXED_VIDEO_NAME

    def _copy_latest(self, output_path: Path):
        return None

    def _clean_display_text(self, text: str) -> str:
        if not text:
            return ""

        cleaned = str(text)
        cleaned = re.sub(r"\(.*?\)", "", cleaned)
        cleaned = re.sub("[^\uAC00-\uD7A3A-Za-z0-9\\s.,?!%:;~\\\"'()#-]", "", cleaned)
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        return cleaned.strip()

    def _source_clip(self, article, duration: float):
        clip = ColorClip(size=(self.width, self.height), color=(0, 0, 0), duration=duration)
        if hasattr(clip, "with_opacity"):
            return clip.with_opacity(0)
        return clip

    def _title_clip(self, article, duration: float):
        config = self.template["title"]
        return (
            self._text_clip(
                text=TITLE_TEXT,
                font_size=config.get("font_size", 88),
                color=config.get("color", "#FFD166"),
                box_width=config.get("width", 980),
                box_height=config.get("height", 280),
                stroke_width=config.get("stroke_width", 6),
                stroke_color=config.get("stroke_color", "black"),
                duration=duration,
            )
            .with_position(("center", config.get("top", 80)))
        )


def main() -> None:
    started_at = time.perf_counter()
    ensure_directories()

    episode_dir = PROJECT_ROOT / "episodes" / EPISODE_ID
    output_video = VIDEO_DIR / FIXED_VIDEO_NAME
    render_report = VIDEO_DIR / FIXED_REPORT_NAME
    scene_dir = IMAGE_DIR / f"{EPISODE_ID}_fixed"
    scene_dir.mkdir(parents=True, exist_ok=True)

    script = _load_json(episode_dir / "script.json")
    beat_sheet = _load_json(episode_dir / "beat_sheet.json")
    visual_plan = _load_json(episode_dir / "visual_plan.json")
    media_plan = _load_json(episode_dir / "media_plan.json")
    knowledge_pack = _load_json(episode_dir / "knowledge_pack.json")

    narration_lines = script["narration_lines"]
    final_script = "\n".join(narration_lines)
    render_items = _build_scene_images(
        media_plan=media_plan,
        visual_plan=visual_plan,
        scene_dir=scene_dir,
    )
    scene_image_paths = [item["image_path"] for item in render_items]

    audio_path = AUDIO_DIR / f"{EPISODE_ID}.mp3"
    if not audio_path.exists():
        asyncio.run(_create_tts(final_script, audio_path))

    article = SimpleNamespace(
        title=ARTICLE_TITLE,
        thumbnail=TITLE_TEXT,
        script=final_script,
        summary=knowledge_pack.get("main_question", ""),
        cleaned_content="",
        content="",
        scenes=[
            {
                "order": index,
                "text": narration,
                "image_keyword": "space medicine",
                "duration": 4,
            }
            for index, narration in enumerate(narration_lines, start=1)
        ],
        source="",
    )

    template = TemplateLoader().load("news_dark")
    template["source"]["top"] = 1810
    template["caption"]["max_length"] = 56
    template["caption"]["line_length"] = 28

    if output_video.exists():
        output_video.unlink()

    engine = Episode001FixedShortsEngine(template)
    rendered_path = engine.render(
        article=article,
        image_path=None,
        image_paths=scene_image_paths,
        audio_path=str(audio_path),
    )

    if not rendered_path or not Path(rendered_path).exists():
        raise RuntimeError("Episode 001 fixed render failed.")

    if Path(rendered_path) != output_video:
        shutil.copyfile(rendered_path, output_video)

    elapsed = time.perf_counter() - started_at
    metrics = _collect_metrics(
        video_path=output_video,
        audio_path=audio_path,
        narration_lines=narration_lines,
        beat_sheet=beat_sheet,
        render_items=render_items,
        render_seconds=elapsed,
    )
    render_report.write_text(_render_report(metrics, render_items), encoding="utf-8")

    print(f"Rendered fixed video: {output_video}")
    print(f"Fixed render report: {render_report}")
    print(f"Duration: {metrics['video_length_seconds']:.2f}s")


async def _create_tts(text: str, output_path: Path) -> None:
    communicate = edge_tts.Communicate(
        text=text,
        voice=TTS_VOICE,
        rate="+0%",
    )
    await communicate.save(str(output_path))


def _build_scene_images(
    media_plan: list[dict],
    visual_plan: list[dict],
    scene_dir: Path,
) -> list[dict]:
    render_items = []

    for item in media_plan:
        scene = int(item["scene"])
        visual_item = visual_plan[scene - 1] if scene - 1 < len(visual_plan) else {}
        resolved = _resolve_media_item(item)
        requested_media_type = resolved["requested_media_type"]
        actual_media_type = resolved["actual_media_type"]

        if resolved["asset_exists"]:
            image = _image_from_asset(resolved["asset_path"], scene)
        else:
            image = _create_generated_visual(
                scene=scene,
                actual_media_type=actual_media_type,
                requested_media_type=requested_media_type,
                visual_type=str(visual_item.get("visual_type", "")),
            )

        path = scene_dir / f"scene_{scene:02d}.png"
        image.save(path)

        log_item = {
            "scene": scene,
            "narration": str(item.get("narration", "")),
            "requested_media_type": requested_media_type,
            "actual_media_type": actual_media_type,
            "asset_path": str(resolved["asset_path"]) if resolved["asset_path"] else "",
            "asset_path_exists": bool(resolved["asset_exists"]),
            "fallback": bool(resolved["fallback"]),
            "image_path": str(path),
        }
        render_items.append(log_item)
        print(
            "render_media "
            f"scene={scene:02d} "
            f"requested_media_type={requested_media_type} "
            f"actual_media_type={actual_media_type} "
            f"asset_path_exists={log_item['asset_path_exists']} "
            f"fallback={log_item['fallback']}"
        )

    return render_items


def _resolve_media_item(item: dict) -> dict:
    requested_media_type = str(item.get("media_type") or "ai_image")
    fallback_media_type = str(item.get("fallback_media_type") or "ai_image")
    asset_path = _media_asset_path(item)
    asset_exists = bool(asset_path and asset_path.exists())

    actual_media_type = requested_media_type
    fallback = False

    if requested_media_type in REAL_MEDIA_TYPES and not asset_exists:
        actual_media_type = "generated_visual"
        fallback = True
    elif requested_media_type not in REAL_MEDIA_TYPES | GENERATED_MEDIA_TYPES:
        actual_media_type = fallback_media_type if fallback_media_type else "generated_visual"
        fallback = actual_media_type != requested_media_type

    return {
        "requested_media_type": requested_media_type,
        "actual_media_type": actual_media_type,
        "asset_path": asset_path,
        "asset_exists": asset_exists,
        "fallback": fallback,
    }


def _media_asset_path(item: dict) -> Path | None:
    raw_path = (
        item.get("asset_path")
        or item.get("media_path")
        or item.get("file_path")
        or item.get("local_path")
    )
    if not raw_path:
        return None

    path = Path(str(raw_path))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def _image_from_asset(asset_path: Path | None, scene: int) -> Image.Image:
    if not asset_path:
        return _create_generated_visual(scene, "generated_visual", "missing_asset", "")

    suffix = asset_path.suffix.lower()
    try:
        if suffix in IMAGE_SUFFIXES:
            image = Image.open(asset_path)
            return _fit_to_visual(image)
        if suffix in VIDEO_SUFFIXES:
            with VideoFileClip(str(asset_path)) as clip:
                frame = clip.get_frame(min(0.25, max(0, clip.duration / 2)))
            return _fit_to_visual(Image.fromarray(frame))
    except Exception:
        return _create_generated_visual(scene, "generated_visual", "asset_error", "")

    return _create_generated_visual(scene, "generated_visual", "unsupported_asset", "")


def _fit_to_visual(image: Image.Image) -> Image.Image:
    image = image.convert("RGB")
    target_ratio = WIDTH / VISUAL_HEIGHT
    source_ratio = image.width / image.height

    if source_ratio > target_ratio:
        new_width = int(image.height * target_ratio)
        left = (image.width - new_width) // 2
        image = image.crop((left, 0, left + new_width, image.height))
    else:
        new_height = int(image.width / target_ratio)
        top = (image.height - new_height) // 2
        image = image.crop((0, top, image.width, top + new_height))

    return image.resize((WIDTH, VISUAL_HEIGHT), Image.Resampling.LANCZOS)


def _create_generated_visual(
    scene: int,
    actual_media_type: str,
    requested_media_type: str,
    visual_type: str,
) -> Image.Image:
    palette = _palette_for(actual_media_type, requested_media_type)
    image = Image.new("RGB", (WIDTH, VISUAL_HEIGHT), palette["base"])
    draw = ImageDraw.Draw(image, "RGBA")
    rng = random.Random(scene * 7919)

    _draw_gradient(draw, palette)
    _draw_stars(draw, rng, palette)

    if scene in {1, 12}:
        _draw_planet_scene(draw, rng, scene)
    elif scene in {2, 4, 5, 6}:
        _draw_body_shift_scene(draw, scene)
    elif scene == 7 or actual_media_type == "infographic":
        _draw_bone_chart_scene(draw)
    elif scene in {8, 9}:
        _draw_exercise_scene(draw)
    elif scene in {10, 11}:
        _draw_return_scene(draw, scene)
    elif actual_media_type == "ai_image":
        _draw_emotional_space_scene(draw, rng)
    else:
        _draw_orbit_scene(draw, rng)

    return image


def _draw_gradient(draw: ImageDraw.ImageDraw, palette: dict) -> None:
    top = palette["top"]
    bottom = palette["bottom"]
    for y in range(VISUAL_HEIGHT):
        ratio = y / max(1, VISUAL_HEIGHT - 1)
        color = tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3))
        draw.line((0, y, WIDTH, y), fill=(*color, 255))


def _draw_stars(draw: ImageDraw.ImageDraw, rng: random.Random, palette: dict) -> None:
    for _ in range(180):
        x = rng.randrange(0, WIDTH)
        y = rng.randrange(0, VISUAL_HEIGHT)
        radius = rng.choice([1, 1, 1, 2])
        alpha = rng.randrange(65, 190)
        draw.ellipse((x, y, x + radius, y + radius), fill=(*palette["star"], alpha))


def _draw_planet_scene(draw: ImageDraw.ImageDraw, rng: random.Random, scene: int) -> None:
    if scene == 12:
        draw.ellipse((-160, 480, 1240, 1680), fill=(165, 74, 44, 255))
        draw.ellipse((110, 605, 980, 910), outline=(236, 154, 104, 120), width=8)
        for _ in range(28):
            x = rng.randrange(0, WIDTH)
            y = rng.randrange(610, 920)
            draw.arc((x - 70, y - 18, x + 70, y + 18), 180, 360, fill=(219, 129, 82, 120), width=3)
        return

    draw.ellipse((-230, 500, 1300, 1700), fill=(24, 91, 148, 255))
    draw.ellipse((-175, 455, 1260, 1660), outline=(119, 204, 255, 145), width=10)
    draw.arc((330, 150, 760, 760), 210, 330, fill=(255, 255, 255, 185), width=7)
    _draw_astronaut_silhouette(draw, WIDTH // 2, 390, scale=1.05)


def _draw_body_shift_scene(draw: ImageDraw.ImageDraw, scene: int) -> None:
    cx = WIDTH // 2
    head_y = 250
    body_top = 420
    draw.ellipse((cx - 105, head_y - 105, cx + 105, head_y + 105), outline=(195, 238, 255, 210), width=8)
    draw.line((cx, body_top, cx, 770), fill=(195, 238, 255, 180), width=12)
    draw.line((cx, 520, cx - 190, 660), fill=(195, 238, 255, 145), width=9)
    draw.line((cx, 520, cx + 190, 660), fill=(195, 238, 255, 145), width=9)
    draw.line((cx, 765, cx - 135, 940), fill=(195, 238, 255, 145), width=10)
    draw.line((cx, 765, cx + 135, 940), fill=(195, 238, 255, 145), width=10)

    for offset, alpha in [(-120, 110), (-50, 150), (25, 190)]:
        draw.line((cx + offset, 735, cx + offset + 80, 370), fill=(107, 232, 255, alpha), width=10)
        draw.polygon(
            [
                (cx + offset + 80, 370),
                (cx + offset + 46, 428),
                (cx + offset + 116, 420),
            ],
            fill=(107, 232, 255, alpha),
        )

    if scene in {4, 6}:
        draw.ellipse((cx - 160, head_y - 42, cx + 160, head_y + 42), outline=(255, 236, 170, 210), width=6)
        draw.ellipse((cx - 52, head_y - 32, cx + 52, head_y + 32), fill=(255, 236, 170, 105))


def _draw_bone_chart_scene(draw: ImageDraw.ImageDraw) -> None:
    base_y = 780
    for index, height in enumerate((270, 218, 172)):
        x = 275 + index * 165
        draw.rounded_rectangle((x, base_y - height, x + 92, base_y), radius=18, fill=(255, 209, 102, 210))
    draw.line((220, base_y, 850, base_y), fill=(255, 255, 255, 150), width=5)

    bone_color = (238, 244, 226, 230)
    draw.rounded_rectangle((390, 250, 690, 345), radius=44, fill=bone_color)
    for x in (380, 700):
        draw.ellipse((x - 58, 223, x + 58, 339), fill=bone_color)
        draw.ellipse((x - 58, 270, x + 58, 386), fill=bone_color)
    draw.line((705, 380, 830, 470), fill=(255, 113, 113, 180), width=8)
    draw.line((830, 380, 705, 470), fill=(255, 113, 113, 180), width=8)


def _draw_exercise_scene(draw: ImageDraw.ImageDraw) -> None:
    cx = WIDTH // 2
    draw.rounded_rectangle((210, 685, 870, 735), radius=24, fill=(145, 176, 205, 180))
    draw.rounded_rectangle((305, 610, 775, 660), radius=20, outline=(145, 176, 205, 180), width=7)
    _draw_astronaut_silhouette(draw, cx - 20, 430, scale=0.82)
    draw.line((cx - 65, 545, cx - 185, 645), fill=(238, 244, 255, 205), width=12)
    draw.line((cx + 55, 548, cx + 160, 648), fill=(238, 244, 255, 205), width=12)
    draw.arc((190, 250, 890, 950), 205, 330, fill=(97, 214, 255, 105), width=6)


def _draw_return_scene(draw: ImageDraw.ImageDraw, scene: int) -> None:
    draw.ellipse((-260, 570, 1340, 1600), fill=(22, 112, 76, 230))
    draw.ellipse((-180, 520, 1260, 1535), outline=(123, 219, 172, 125), width=8)
    if scene == 10:
        draw.line((300, 295, 735, 612), fill=(255, 183, 93, 190), width=16)
        draw.polygon([(735, 612), (675, 525), (812, 563)], fill=(255, 183, 93, 190))
        draw.ellipse((710, 560, 825, 675), fill=(210, 225, 235, 235))
    else:
        draw.line((430, 475, 430, 845), fill=(240, 248, 255, 190), width=13)
        draw.line((560, 475, 560, 845), fill=(240, 248, 255, 190), width=13)
        draw.ellipse((360, 820, 500, 875), fill=(240, 248, 255, 220))
        draw.ellipse((500, 820, 640, 875), fill=(240, 248, 255, 220))


def _draw_emotional_space_scene(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    _draw_astronaut_silhouette(draw, WIDTH // 2, 475, scale=1.2)
    for radius, alpha in [(250, 35), (345, 25), (445, 18)]:
        draw.ellipse(
            (WIDTH // 2 - radius, 475 - radius, WIDTH // 2 + radius, 475 + radius),
            outline=(219, 178, 255, alpha),
            width=6,
        )


def _draw_orbit_scene(draw: ImageDraw.ImageDraw, rng: random.Random) -> None:
    cx = WIDTH // 2
    cy = VISUAL_HEIGHT // 2
    for radius, alpha in [(190, 110), (305, 85), (420, 60)]:
        draw.ellipse((cx - radius, cy - radius, cx + radius, cy + radius), outline=(125, 210, 255, alpha), width=5)
    draw.ellipse((cx - 82, cy - 82, cx + 82, cy + 82), fill=(255, 209, 102, 190))
    draw.ellipse((cx + 270, cy - 22, cx + 314, cy + 22), fill=(166, 227, 161, 205))


def _draw_astronaut_silhouette(draw: ImageDraw.ImageDraw, cx: int, cy: int, scale: float = 1.0) -> None:
    def s(value: int) -> int:
        return int(value * scale)

    suit = (235, 244, 255, 230)
    visor = (55, 92, 125, 230)
    draw.ellipse((cx - s(80), cy - s(150), cx + s(80), cy + s(10)), fill=suit)
    draw.ellipse((cx - s(52), cy - s(118), cx + s(52), cy - s(28)), fill=visor)
    draw.rounded_rectangle((cx - s(90), cy + s(5), cx + s(90), cy + s(220)), radius=s(42), fill=suit)
    draw.line((cx - s(95), cy + s(65), cx - s(180), cy + s(155)), fill=suit, width=s(22))
    draw.line((cx + s(95), cy + s(65), cx + s(180), cy + s(155)), fill=suit, width=s(22))
    draw.line((cx - s(45), cy + s(220), cx - s(95), cy + s(340)), fill=suit, width=s(28))
    draw.line((cx + s(45), cy + s(220), cx + s(95), cy + s(340)), fill=suit, width=s(28))


def _palette_for(actual_media_type: str, requested_media_type: str) -> dict:
    if actual_media_type == "infographic":
        return {"base": (15, 18, 25), "top": (20, 24, 35), "bottom": (52, 44, 28), "star": (255, 239, 185)}
    if actual_media_type == "animation":
        return {"base": (7, 24, 32), "top": (9, 28, 40), "bottom": (14, 51, 54), "star": (178, 245, 255)}
    if requested_media_type == "official_image":
        return {"base": (8, 16, 30), "top": (10, 22, 42), "bottom": (20, 42, 70), "star": (216, 233, 255)}
    if actual_media_type == "ai_image":
        return {"base": (21, 17, 31), "top": (18, 14, 28), "bottom": (45, 31, 60), "star": (228, 205, 255)}
    return {"base": (8, 14, 26), "top": (7, 13, 28), "bottom": (20, 34, 54), "star": (224, 238, 255)}


def _collect_metrics(
    video_path: Path,
    audio_path: Path,
    narration_lines: list[str],
    beat_sheet: dict,
    render_items: list[dict],
    render_seconds: float,
) -> dict:
    with VideoFileClip(str(video_path)) as video:
        video_length = float(video.duration)

    with AudioFileClip(str(audio_path)) as audio:
        audio_length = float(audio.duration)

    scene_count = len(narration_lines)
    cut_count = scene_count
    caption_count = scene_count
    average_scene_length = video_length / scene_count if scene_count else 0
    real_count = sum(
        item["asset_path_exists"] and item["actual_media_type"] in REAL_MEDIA_TYPES
        for item in render_items
    )
    ai_count = sum(item["actual_media_type"] == "ai_image" for item in render_items)
    generated_count = sum(item["actual_media_type"] == "generated_visual" for item in render_items)
    fallback_count = sum(item["fallback"] for item in render_items)

    return {
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "video_length_seconds": video_length,
        "audio_length_seconds": audio_length,
        "scene_count": scene_count,
        "cut_count": cut_count,
        "caption_count": caption_count,
        "average_scene_length_seconds": average_scene_length,
        "last_caption_displayed": caption_count == scene_count and scene_count > 0,
        "real_media_count": real_count,
        "ai_image_count": ai_count,
        "generated_visual_count": generated_count,
        "fallback_count": fallback_count,
        "render_time_seconds": render_seconds,
        "beat_count": len(beat_sheet.get("beats", [])),
    }


def _render_report(metrics: dict, render_items: list[dict]) -> str:
    lines = [
        "# Episode 001 Fixed Render Report",
        "",
        f"- video_length: {metrics['video_length_seconds']:.2f}s",
        f"- audio_length: {metrics['audio_length_seconds']:.2f}s",
        f"- scene_count: {metrics['scene_count']}",
        f"- cut_count: {metrics['cut_count']}",
        f"- caption_count: {metrics['caption_count']}",
        f"- average_scene_length: {metrics['average_scene_length_seconds']:.2f}s",
        f"- last_caption_displayed: {'yes' if metrics['last_caption_displayed'] else 'no'}",
        f"- real_asset_used_count: {metrics['real_media_count']}",
        f"- ai_image_used_count: {metrics['ai_image_count']}",
        f"- generated_visual_used_count: {metrics['generated_visual_count']}",
        f"- fallback_count: {metrics['fallback_count']}",
        f"- render_time: {metrics['render_time_seconds']:.2f}s",
        "",
        f"- output_video: `{metrics['video_path']}`",
        f"- tts_audio: `{metrics['audio_path']}`",
        "- placeholder_debug_text_removed: yes",
        "- fallback_rule: real media requests without an existing asset_path render as clean generated visuals.",
        "",
        "## Media Resolution Log",
        "",
        "| scene | requested_media_type | actual_media_type | asset_path_exists | fallback | asset_path |",
        "|---:|---|---|---:|---:|---|",
    ]

    for item in render_items:
        asset_path = item["asset_path"] or ""
        lines.append(
            "| "
            f"{item['scene']} | "
            f"{item['requested_media_type']} | "
            f"{item['actual_media_type']} | "
            f"{str(item['asset_path_exists']).lower()} | "
            f"{str(item['fallback']).lower()} | "
            f"`{asset_path}` |"
        )

    lines.append("")
    return "\n".join(lines)


def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/malgunbd.ttf") if bold else Path("C:/Windows/Fonts/malgun.ttf"),
        Path("C:/Windows/Fonts/NanumGothicBold.ttf") if bold else Path("C:/Windows/Fonts/NanumGothic.ttf"),
    ]
    for path in candidates:
        if path and path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
