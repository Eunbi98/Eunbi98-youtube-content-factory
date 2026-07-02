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
    VIDEO_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
    VIDEO_SOURCE_FONT_SIZE,
    VIDEO_TITLE_COLOR,
    VIDEO_TITLE_FONT_SIZE,
    VIDEO_TITLE_MAX_LENGTH,
    VIDEO_WIDTH,
)


class VideoService:
    def __init__(self):
        self.output_dir = VIDEO_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.width = VIDEO_WIDTH
        self.height = VIDEO_HEIGHT

    def create_video(self, article, image_path: str | None, audio_path: str | None) -> str | None:
        if not audio_path:
            return None

        output_path = self.output_dir / DEFAULT_VIDEO_FILENAME

        audio = None
        video = None

        try:
            audio = AudioFileClip(audio_path)
            duration = audio.duration

            clips = []

            background = ColorClip(
                size=(self.width, self.height),
                color=VIDEO_BACKGROUND_COLOR,
                duration=duration
            )
            clips.append(background)

            if image_path:
                main_image = self._create_main_image_clip(
                    image_path=image_path,
                    duration=duration
                )
                clips.append(main_image)

            title_clip = self._create_title_clip(
                article=article,
                duration=duration
            )
            clips.append(title_clip)

            caption_clip = self._create_caption_clip(
                article=article,
                duration=duration
            )
            clips.append(caption_clip)

            source_clip = self._create_source_clip(
                article=article,
                duration=duration
            )
            clips.append(source_clip)

            video = CompositeVideoClip(
                clips,
                size=(self.width, self.height)
            ).with_audio(audio)

            video.write_videofile(
                str(output_path),
                fps=VIDEO_FPS,
                codec="libx264",
                audio_codec="aac"
            )

            return str(output_path)

        finally:
            if video:
                video.close()

            if audio:
                audio.close()

    def _create_main_image_clip(self, image_path: str, duration: float):
        image = ImageClip(image_path)

        image_ratio = image.w / image.h
        target_ratio = self.width / 1100

        if image_ratio > target_ratio:
            image = image.resized(height=1100)
        else:
            image = image.resized(width=self.width)

        image = (
            image
            .with_duration(duration)
            .with_position(("center", 420))
        )

        return image

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
                stroke_width=4,
            )
            .with_duration(duration)
            .with_position(("center", 110))
        )

    def _create_caption_clip(self, article, duration: float):
        caption_text = article.script or article.summary
        caption_text = self._shorten_text(
            caption_text,
            VIDEO_CAPTION_MAX_LENGTH
        )

        return (
            TextClip(
                text=caption_text,
                font_size=VIDEO_CAPTION_FONT_SIZE,
                color=VIDEO_CAPTION_COLOR,
                size=(980, 320),
                method="caption",
                text_align="center",
                stroke_color="black",
                stroke_width=3,
            )
            .with_duration(duration)
            .with_position(("center", 1520))
        )

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
            .with_position(("center", 1810))
        )

    def _shorten_text(self, text: str, max_length: int) -> str:
        if not text:
            return ""

        text = " ".join(str(text).split())

        if len(text) <= max_length:
            return text

        return text[:max_length].rstrip() + "..."