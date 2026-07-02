from datetime import datetime
from pathlib import Path
import os
import shutil

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
)

from app.video.assets import VideoAssets
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
        self.template = template
        self.assets = VideoAssets()

        self.output_dir = VIDEO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT

    def render(
        self,
        article,
        image_path: str | None,
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

            clips = [
                self._background_clip(duration)
            ]

            if image_path:
                clips.extend(
                    self._image_scene_clips(
                        image_path=image_path,
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

    def _background_clip(self, duration: float):
        bg = self.template.get("background", {})
        color = tuple(bg.get("color", [10, 10, 14]))

        return ColorClip(
            size=(self.width, self.height),
            color=color,
            duration=duration
        )

    def _image_scene_clips(self, image_path: str, duration: float):
        config = self.template["image"]

        scene_seconds = 4
        clips = []
        start_time = 0

        while start_time < duration:
            clip_duration = min(scene_seconds, duration - start_time)

            image_clip = self._image_clip(
                image_path=image_path,
                duration=clip_duration,
                scene_index=len(clips)
            ).with_start(start_time)

            clips.append(image_clip)
            start_time += scene_seconds

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

        text = article.thumbnail or article.title
        text = self._shorten_text(
            text=text,
            max_length=config.get("max_length", 34)
        )

        return (
            self._text_clip(
                text=text,
                font_size=config.get("font_size", 76),
                color=config.get("color", "white"),
                box_width=config.get("width", 980),
                box_height=config.get("height", 260),
                stroke_width=config.get("stroke_width", 5),
                stroke_color=config.get("stroke_color", "black"),
                duration=duration,
            )
            .with_position(("center", config.get("top", 90)))
        )

    def _caption_clips(self, article, duration: float):
        config = self.template["caption"]

        lines = self._split_script(article.script or article.summary)

        if not lines:
            return []

        clips = []
        segment_duration = config.get("seconds", 4)
        start_time = 0

        for line in lines:
            if start_time >= duration:
                break

            text = self._shorten_text(
                text=line,
                max_length=config.get("max_length", 42)
            )

            clip_duration = min(
                segment_duration,
                duration - start_time
            )

            clip = (
                self._text_clip(
                    text=text,
                    font_size=config.get("font_size", 58),
                    color=config.get("color", "white"),
                    box_width=config.get("width", 980),
                    box_height=config.get("height", 260),
                    stroke_width=config.get("stroke_width", 4),
                    stroke_color=config.get("stroke_color", "black"),
                    duration=clip_duration,
                )
                .with_start(start_time)
                .with_position(("center", config.get("top", 1430)))
            )

            clips.append(clip)
            start_time += segment_duration

        return clips

    def _source_clip(self, article, duration: float):
        config = self.template["source"]

        text = f"출처: {article.source}"

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

        lines = []

        for raw_line in script.splitlines():
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
            for sentence in script.replace("?", "?.").replace("!", "!.").split(".")
            if sentence.strip()
        ]

    def _shorten_text(self, text: str, max_length: int) -> str:
        if not text:
            return ""

        text = " ".join(str(text).split())

        if len(text) <= max_length:
            return text

        return text[:max_length].rstrip() + "..."

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