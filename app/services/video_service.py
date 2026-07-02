import os
from datetime import datetime
from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
)

from config.settings import (
    DEFAULT_VIDEO_FILENAME,
    VIDEO_BACKGROUND_COLOR,
    VIDEO_CAPTION_COLOR,
    VIDEO_CAPTION_FONT_SIZE,
    VIDEO_CAPTION_MAX_LENGTH,
    VIDEO_CAPTION_SECONDS,
    VIDEO_CAPTION_TOP,
    VIDEO_DIR,
    VIDEO_FILENAME_PREFIX,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_IMAGE_HEIGHT,
    VIDEO_IMAGE_TOP,
    VIDEO_REMOVE_TEMP_FILES,
    VIDEO_SOURCE_FONT_SIZE,
    VIDEO_SOURCE_TOP,
    VIDEO_TITLE_COLOR,
    VIDEO_TITLE_FONT_SIZE,
    VIDEO_TITLE_MAX_LENGTH,
    VIDEO_TITLE_TOP,
    VIDEO_WIDTH,
)


class VideoService:
    def __init__(self):
        self.output_dir = VIDEO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT

    def create_video(
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
                self._create_background(duration)
            ]

            if image_path:
                clips.append(
                    self._create_main_image_clip(
                        image_path=image_path,
                        duration=duration
                    )
                )

            clips.append(
                self._create_title_clip(
                    article=article,
                    duration=duration
                )
            )

            clips.extend(
                self._create_caption_clips(
                    article=article,
                    duration=duration
                )
            )

            clips.append(
                self._create_source_clip(
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

            self._remove_moviepy_temp_files()

            latest_path = self.output_dir / DEFAULT_VIDEO_FILENAME
            self._copy_latest(output_path, latest_path)

            return str(output_path)

        finally:
            if video:
                video.close()

            if audio:
                audio.close()

    def _make_output_path(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{VIDEO_FILENAME_PREFIX}_{timestamp}.mp4"

        return self.output_dir / filename

    def _copy_latest(self, source_path: Path, latest_path: Path):
        try:
            with open(source_path, "rb") as source:
                with open(latest_path, "wb") as target:
                    target.write(source.read())
        except Exception:
            pass

    def _remove_moviepy_temp_files(self):
        project_root = Path.cwd()

        for path in project_root.glob("newsTEMP_MPY*.mp4"):
            try:
                os.remove(path)
            except OSError:
                pass

        for path in project_root.glob("*TEMP_MPY*.mp4"):
            try:
                os.remove(path)
            except OSError:
                pass

    def _create_background(self, duration: float):
        return ColorClip(
            size=(self.width, self.height),
            color=VIDEO_BACKGROUND_COLOR,
            duration=duration
        )

    def _create_main_image_clip(self, image_path: str, duration: float):
        image = ImageClip(image_path)

        target_ratio = self.width / VIDEO_IMAGE_HEIGHT
        image_ratio = image.w / image.h

        if image_ratio > target_ratio:
            image = image.resized(height=VIDEO_IMAGE_HEIGHT)
        else:
            image = image.resized(width=self.width)

        return (
            image
            .with_duration(duration)
            .with_position(("center", VIDEO_IMAGE_TOP))
        )

    def _create_title_clip(self, article, duration: float):
        title_text = article.thumbnail or article.title
        title_text = self._shorten_text(
            title_text,
            VIDEO_TITLE_MAX_LENGTH
        )

        return (
            TextClip(
                text=title_text,
                font_size=VIDEO_TITLE_FONT_SIZE,
                color=VIDEO_TITLE_COLOR,
                size=(980, 260),
                method="caption",
                text_align="center",
                stroke_color="black",
                stroke_width=5,
            )
            .with_duration(duration)
            .with_position(("center", VIDEO_TITLE_TOP))
        )

    def _create_caption_clips(self, article, duration: float):
        caption_lines = self._split_script(article.script or article.summary)

        if not caption_lines:
            return []

        clips = []
        start_time = 0

        for line in caption_lines:
            if start_time >= duration:
                break

            safe_line = self._shorten_text(
                line,
                VIDEO_CAPTION_MAX_LENGTH
            )

            clip_duration = min(
                VIDEO_CAPTION_SECONDS,
                duration - start_time
            )

            caption_clip = (
                TextClip(
                    text=safe_line,
                    font_size=VIDEO_CAPTION_FONT_SIZE,
                    color=VIDEO_CAPTION_COLOR,
                    size=(980, 260),
                    method="caption",
                    text_align="center",
                    stroke_color="black",
                    stroke_width=4,
                )
                .with_start(start_time)
                .with_duration(clip_duration)
                .with_position(("center", VIDEO_CAPTION_TOP))
            )

            clips.append(caption_clip)
            start_time += VIDEO_CAPTION_SECONDS

        return clips

    def _create_source_clip(self, article, duration: float):
        source_text = f"출처: {article.source}"

        return (
            TextClip(
                text=source_text,
                font_size=VIDEO_SOURCE_FONT_SIZE,
                color="white",
                size=(900, 80),
                method="caption",
                text_align="center",
                stroke_color="black",
                stroke_width=2,
            )
            .with_duration(duration)
            .with_position(("center", VIDEO_SOURCE_TOP))
        )

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