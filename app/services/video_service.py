from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip,
)

from config.settings import (
    DEFAULT_VIDEO_FILENAME,
    VIDEO_DIR,
    VIDEO_FPS,
    VIDEO_HEIGHT,
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

            background = ColorClip(
                size=(self.width, self.height),
                color=(15, 15, 15),
                duration=duration
            )

            clips = [background]

            if image_path:
                image = (
                    ImageClip(image_path)
                    .with_duration(duration)
                    .resized(width=1080)
                    .with_position(("center", 360))
                )

                clips.append(image)

            title_text = self._shorten_text(article.title, 54)
            script_text = self._shorten_text(article.script, 130)

            title = TextClip(
                text=title_text,
                font_size=54,
                color="white",
                size=(960, 220),
                method="caption",
                text_align="center"
            ).with_duration(duration).with_position(("center", 80))

            script = TextClip(
                text=script_text,
                font_size=48,
                color="white",
                size=(960, 420),
                method="caption",
                text_align="center"
            ).with_duration(duration).with_position(("center", 1250))

            source = TextClip(
                text=f"Source: {article.source}",
                font_size=30,
                color="white",
                size=(900, 80),
                method="caption",
                text_align="center"
            ).with_duration(duration).with_position(("center", 1780))

            clips.append(title)
            clips.append(script)
            clips.append(source)

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

    def _shorten_text(self, text: str, max_length: int) -> str:
        if not text:
            return ""

        text = " ".join(text.split())

        if len(text) <= max_length:
            return text

        return text[:max_length].rstrip() + "..."