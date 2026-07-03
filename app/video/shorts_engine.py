from datetime import datetime
from pathlib import Path
import os
import re
import shutil
import textwrap

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
)

from app.story import KoreanLanguageGuard
from app.story.text_normalizer import normalize_english_terms
from app.video.assets import VideoAssets
from app.video.caption_layout import calculate_caption_box, layout_caption_text
from app.video.caption_timing import build_caption_schedule, fit_caption_texts_to_duration
from app.video.style_config import DEFAULT_VIDEO_STYLE
from app.video.title_generator import VideoTitleGenerator
from config.settings import (
    DEFAULT_VIDEO_FILENAME,
    VIDEO_DIR,
    VIDEO_FILENAME_PREFIX,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_REMOVE_TEMP_FILES,
    VIDEO_WIDTH,
)


class ShortsEngine:
    def __init__(self, template: dict):
        self.template = self._merge_style_defaults(template)
        self.assets = VideoAssets()
        self.title_generator = VideoTitleGenerator()
        self.language_guard = KoreanLanguageGuard()

        self.output_dir = VIDEO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT

    def render(
        self,
        article,
        image_path: str | None,
        image_paths: list[str] | None,
        audio_path: str | None
    ) -> str | None:
        if not audio_path:
            return None

        output_path = self._make_output_path()

        audio = None
        video = None

        try:
            audio = AudioFileClip(audio_path)
            duration = audio.duration
            diagnostics = self._build_render_diagnostics(article, duration)
            self._print_render_diagnostics(diagnostics)

            clips = [
                self._background_clip(duration)
            ]

            scene_image_paths = self._resolve_scene_images(
                image_path=image_path,
                image_paths=image_paths or []
            )

            if scene_image_paths:
                clips.extend(
                    self._image_scene_clips(
                        image_paths=scene_image_paths,
                        duration=duration
                    )
                )

            clips.append(
                self._title_clip(
                    article=article,
                    duration=duration
                )
            )

            clips.extend(
                self._caption_clips(
                    article=article,
                    duration=duration
                )
            )

            clips.append(
                self._source_clip(
                    article=article,
                    duration=duration
                )
            )

            video = CompositeVideoClip(
                clips,
                size=(self.width, self.height)
            ).with_audio(audio)

            temp_audio_path = self.output_dir / "temp_audio.m4a"

            video.write_videofile(
                str(output_path),
                fps=VIDEO_FPS,
                codec="libx264",
                audio_codec="aac",
                temp_audiofile=str(temp_audio_path),
                remove_temp=VIDEO_REMOVE_TEMP_FILES
            )

            self._copy_latest(output_path)
            self._remove_moviepy_temp_files()

            return str(output_path)

        finally:
            if video:
                video.close()

            if audio:
                audio.close()

    def _resolve_scene_images(
        self,
        image_path: str | None,
        image_paths: list[str]
    ) -> list[str]:
        valid_paths = []

        for path in image_paths:
            if path and Path(path).exists():
                valid_paths.append(path)

        if valid_paths:
            return valid_paths

        if image_path and Path(image_path).exists():
            return [image_path]

        return []

    def _background_clip(self, duration: float):
        bg = self.template.get("background", {})
        color = tuple(bg.get("color", [10, 10, 14]))

        return ColorClip(
            size=(self.width, self.height),
            color=color,
            duration=duration
        )

    def _image_scene_clips(self, image_paths: list[str], duration: float):
        scene_durations = self._get_scene_durations(duration)
        clips = []
        start_time = 0

        for index, scene_duration in enumerate(scene_durations):
            if start_time >= duration:
                break

            image_path = image_paths[index % len(image_paths)]

            clip = (
                self._image_clip(
                    image_path=image_path,
                    duration=scene_duration,
                    scene_index=index
                )
                .with_start(start_time)
            )

            clips.append(clip)
            start_time += scene_duration

        return clips

    def _image_clip(
        self,
        image_path: str,
        duration: float,
        scene_index: int = 0
    ):
        config = self.template["image"]

        image = ImageClip(image_path)

        target_width = config.get("width", self.width)
        target_height = config.get("height", 980)

        target_ratio = target_width / target_height
        image_ratio = image.w / image.h

        if image_ratio > target_ratio:
            image = image.resized(height=target_height)
        else:
            image = image.resized(width=target_width)

        zoom_start = config.get("zoom_start", 1.0)
        zoom_end = config.get("zoom_end", 1.08)

        if scene_index % 2 == 1:
            zoom_start, zoom_end = zoom_end, zoom_start

        image = image.resized(
            lambda t: zoom_start + ((zoom_end - zoom_start) * (t / duration))
        )

        return (
            image
            .with_duration(duration)
            .with_position(("center", config.get("top", 390)))
        )

    def _title_clip(self, article, duration: float):
        config = self.template["title"]

        text = self.title_generator.generate(article)
        text = self._clean_display_text(text)
        text = self._shorten_text(
            text=text,
            max_length=config.get("max_length", 32)
        )
        text = self._wrap_korean_text(
            text,
            line_length=config.get("line_length", 11),
            max_lines=2
        )

        return (
            self._text_clip(
                text=text,
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

    def _caption_clips(self, article, duration: float):
        config = self.template["caption"]
        scene_texts = self._fit_scene_texts_to_duration(
            texts=self._get_scene_texts(article),
            duration=duration
        )
        caption_schedule = self._get_caption_schedule(
            text_count=len(scene_texts),
            total_duration=duration
        )

        if not scene_texts:
            return []

        clips = []

        for index, text in enumerate(scene_texts):
            start_time, clip_duration = caption_schedule[index]

            safe_text = self._clean_display_text(text)
            safe_text = self._shorten_text(
                text=safe_text,
                max_length=config.get("max_length", 56)
            )
            safe_text = self._layout_caption_text(
                safe_text,
                config=config,
            )
            caption_box = self._caption_box(config=config, text=safe_text)
            background_enabled = config.get("caption_background_enabled", False)
            text_box_width = (
                caption_box["width"]
                if background_enabled
                else config.get("width", 980)
            )
            text_box_height = (
                caption_box["height"]
                if background_enabled
                else config.get("height", 320)
            )
            self._log_caption_layout(
                index=index + 1,
                text=safe_text,
                box=caption_box,
            )

            text_clip = (
                self._text_clip(
                    text=safe_text,
                    font_size=config.get("font_size", 52),
                    color=config.get("color", "white"),
                    box_width=text_box_width,
                    box_height=text_box_height,
                    stroke_width=config.get("stroke_width", 3),
                    stroke_color=config.get("stroke_color", "black"),
                    duration=clip_duration,
                )
                .with_start(start_time)
                .with_position(("center", config.get("top", 1390)))
            )

            if background_enabled:
                background_clip = self._caption_background_clip(
                    config=config,
                    duration=clip_duration,
                    text=safe_text,
                    box=caption_box,
                ).with_start(start_time)
                clips.append(background_clip)

            clips.append(text_clip)

        return clips

    def _caption_background_clip(
        self,
        config: dict,
        duration: float,
        text: str,
        box: dict[str, int],
    ):
        width = box["width"]
        height = box["height"]
        color = tuple(config.get("background_color", [0, 0, 0]))
        opacity = config.get("background_opacity", 0.68)
        top = config.get("top", 1390) + ((config.get("height", 320) - height) // 2)

        rounded_clip = self._rounded_rectangle_clip(
            width=width,
            height=height,
            color=color,
            opacity=opacity,
            duration=duration,
            radius=config.get("background_radius", 28),
        )

        if rounded_clip:
            return rounded_clip.with_position(("center", top))

        clip = ColorClip(
            size=(width, height),
            color=color,
            duration=duration
        )

        if hasattr(clip, "with_opacity"):
            clip = clip.with_opacity(opacity)
        elif hasattr(clip, "set_opacity"):
            clip = clip.set_opacity(opacity)

        return clip.with_position(("center", top))

    def _rounded_rectangle_clip(
        self,
        width: int,
        height: int,
        color: tuple[int, int, int],
        opacity: float,
        duration: float,
        radius: int,
    ):
        try:
            import numpy as np
            from PIL import Image, ImageDraw
        except Exception:
            return None

        image = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        alpha = int(max(0, min(1, opacity)) * 255)
        draw.rounded_rectangle(
            (0, 0, width, height),
            radius=radius,
            fill=(*color, alpha),
        )

        return ImageClip(np.array(image)).with_duration(duration)

    def _source_clip(self, article, duration: float):
        config = self.template["source"]

        text = f"출처: {article.source}"
        text = self._clean_display_text(text)

        return (
            self._text_clip(
                text=text,
                font_size=config.get("font_size", 30),
                color=config.get("color", "white"),
                box_width=config.get("width", 900),
                box_height=config.get("height", 80),
                stroke_width=config.get("stroke_width", 2),
                stroke_color=config.get("stroke_color", "black"),
                duration=duration,
            )
            .with_position(("center", config.get("top", 1810)))
        )

    def _get_scene_texts(self, article) -> list[str]:
        texts = []

        if article.scenes:
            for scene in article.scenes:
                text = str(scene.get("text", "")).strip()
                text = self._clean_display_text(text)

                if text:
                    texts.append(text)

        if texts:
            return texts

        return [
            self._clean_display_text(line)
            for line in self._split_script(article.script or article.summary)
            if self._clean_display_text(line)
        ]

    def _get_scene_durations(self, total_duration: float) -> list[float]:
        caption_config = self.template.get("caption", {})
        default_seconds = caption_config.get("seconds", 4)

        return [default_seconds] * int((total_duration // default_seconds) + 1)

    def _fit_scene_texts_to_duration(
        self,
        texts: list[str],
        duration: float,
    ) -> list[str]:
        caption_config = self.template.get("caption", {})
        return fit_caption_texts_to_duration(
            texts=texts,
            duration=duration,
            min_seconds=caption_config.get("min_seconds", 1.5),
        )

    def _get_caption_schedule(
        self,
        text_count: int,
        total_duration: float,
    ) -> list[tuple[float, float]]:
        if text_count <= 0 or total_duration <= 0:
            return []

        caption_config = self.template.get("caption", {})
        return build_caption_schedule(
            text_count=text_count,
            total_duration=total_duration,
            default_seconds=float(caption_config.get("seconds", 4)),
            min_seconds=float(caption_config.get("min_seconds", 1.5)),
        )

    def _text_clip(
        self,
        text: str,
        font_size: int,
        color: str,
        box_width: int,
        box_height: int,
        stroke_width: int,
        stroke_color: str,
        duration: float,
    ):
        kwargs = {
            "text": text,
            "font_size": font_size,
            "color": color,
            "size": (box_width, box_height),
            "method": "caption",
            "text_align": "center",
            "stroke_color": stroke_color,
            "stroke_width": stroke_width,
        }

        if self.assets.font_path:
            kwargs["font"] = self.assets.font_path

        return TextClip(**kwargs).with_duration(duration)

    def _split_script(self, script: str) -> list[str]:
        if not script:
            return []

        cleaned_script = self._clean_display_text(script)

        lines = []

        for raw_line in cleaned_script.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            if line.startswith("-"):
                line = line[1:].strip()

            if line:
                lines.append(line)

        if lines:
            return lines

        return [
            sentence.strip()
            for sentence in cleaned_script.replace("?", "?.").replace("!", "!.").split(".")
            if sentence.strip()
        ]

    def _clean_display_text(self, text: str) -> str:
        if not text:
            return ""

        text = normalize_english_terms(str(text))

        banned_patterns = [
            r"\(.*?음악.*?\)",
            r"\(.*?BGM.*?\)",
            r"\(.*?효과음.*?\)",
            r"\(.*?자막.*?\)",
            r"\(.*?화면.*?\)",
            r"\(.*?장면.*?\)",
            r"\(.*?이미지.*?\)",
            r"\(.*?내레이션.*?\)",
            r"\(.*?컷.*?\)",
            r"음악\s*삽입[!！]?",
            r"BGM\s*삽입[!！]?",
            r"효과음\s*삽입[!！]?",
            r"자막\s*표시[!！]?",
            r"장면\s*전환[!！]?",
        ]

        for pattern in banned_patterns:
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

        allowed_pattern = r"[^가-힣A-Za-z0-9\s.,?!%:;·~\-\'\"()#]"
        text = re.sub(allowed_pattern, "", text)

        text = re.sub(r"\s+", " ", text)
        text = text.strip()

        return text

    def _wrap_korean_text(
        self,
        text: str,
        line_length: int,
        max_lines: int
    ) -> str:
        if not text:
            return ""

        wrapped = textwrap.wrap(
            text,
            width=line_length,
            break_long_words=False,
            replace_whitespace=False
        )

        wrapped = wrapped[:max_lines]

        return "\n".join(wrapped)

    def _shorten_text(self, text: str, max_length: int) -> str:
        if not text:
            return ""

        text = " ".join(str(text).split())

        if len(text) <= max_length:
            return text

        return text[:max_length].rstrip() + "..."

    def _layout_caption_text(self, text: str, config: dict) -> str:
        return layout_caption_text(
            text=text,
            one_line_max=config.get("line_length", 28),
            preferred_min=18,
            preferred_max=24,
            two_line_max=config.get("max_length", 32),
            min_second_line=10,
        )

    def _caption_box(self, config: dict, text: str) -> dict[str, int]:
        return calculate_caption_box(
            wrapped_text=text,
            screen_width=self.width,
            font_size=config.get("font_size", 52),
            padding_x=config.get("background_padding_x", 56),
            padding_y=config.get("background_padding_y", 24),
            min_width_ratio=config.get("background_min_width_ratio", 0.55),
            max_width_ratio=config.get("background_max_width_ratio", 0.88),
        )

    def _log_caption_layout(
        self,
        index: int,
        text: str,
        box: dict[str, int],
    ) -> None:
        compact_text = text.replace("\n", " / ")
        print(
            "caption_layout "
            f"{index}: text='{compact_text}' "
            f"lines={box['line_count']} "
            f"box={box['width']}x{box['height']}"
        )

    def _merge_style_defaults(self, template: dict) -> dict:
        merged = dict(template)

        for section, defaults in DEFAULT_VIDEO_STYLE.items():
            section_config = dict(defaults)
            section_config.update(merged.get(section, {}))
            merged[section] = section_config

        return merged

    def _build_render_diagnostics(self, article, duration: float) -> dict:
        script_lines = self._split_script(getattr(article, "script", ""))
        scene_texts = self._get_scene_texts(article)
        fitted_scene_texts = self._fit_scene_texts_to_duration(scene_texts, duration)
        caption_schedule = self._get_caption_schedule(
            text_count=len(fitted_scene_texts),
            total_duration=duration,
        )
        script = "\n".join(script_lines)
        metrics = self.language_guard.inspect(script)
        last_caption_end = 0.0

        if caption_schedule:
            last_start, last_duration = caption_schedule[-1]
            last_caption_end = last_start + last_duration

        return {
            "title": self.title_generator.generate(article),
            "final_script_preview": script[:180],
            "final_tts_preview": script[:180],
            "script_line_count": len(script_lines),
            "scene_count": len(fitted_scene_texts),
            "last_script_line": script_lines[-1] if script_lines else "",
            "last_scene_text": fitted_scene_texts[-1] if fitted_scene_texts else "",
            "last_caption_text": fitted_scene_texts[-1] if fitted_scene_texts else "",
            "last_caption_end": last_caption_end,
            "silent_visual_tail_duration": max(0.0, duration - last_caption_end),
            "korean_ratio": metrics["korean_ratio"],
            "english_ratio": metrics["english_ratio"],
            "audio_duration": duration,
            "video_duration": duration,
        }

    def _print_render_diagnostics(self, diagnostics: dict) -> None:
        print("\nVideo Render Diagnostics")
        print(f"최종 title: {diagnostics['title']}")
        print(f"final_script_preview: {diagnostics['final_script_preview']}")
        print(f"final_tts_preview: {diagnostics['final_tts_preview']}")
        print(f"korean_ratio: {diagnostics['korean_ratio']:.2f}")
        print(f"english_ratio: {diagnostics['english_ratio']:.2f}")
        print(f"최종 script 문장 수: {diagnostics['script_line_count']}")
        print(f"scenes 문장 수: {diagnostics['scene_count']}")
        print(f"마지막 script 문장: {diagnostics['last_script_line']}")
        print(f"마지막 scene text: {diagnostics['last_scene_text']}")
        print(f"video_duration: {diagnostics['video_duration']:.2f}초")
        print(f"last_caption_end: {diagnostics['last_caption_end']:.2f}초")
        print(f"last_caption_text: {diagnostics['last_caption_text']}")
        print(
            "silent_visual_tail_duration: "
            f"{diagnostics['silent_visual_tail_duration']:.2f}초"
        )
        print(f"전체 음성 길이: {diagnostics['audio_duration']:.2f}초")
        print(f"전체 영상 길이: {diagnostics['video_duration']:.2f}초")

    def _make_output_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{VIDEO_FILENAME_PREFIX}_{timestamp}.mp4"

        return self.output_dir / filename

    def _copy_latest(self, output_path: Path):
        latest_path = self.output_dir / DEFAULT_VIDEO_FILENAME

        try:
            shutil.copyfile(output_path, latest_path)
        except Exception:
            pass

    def _remove_moviepy_temp_files(self):
        project_root = Path.cwd()

        for path in project_root.glob("*TEMP_MPY*.mp4"):
            try:
                os.remove(path)
            except OSError:
                pass
