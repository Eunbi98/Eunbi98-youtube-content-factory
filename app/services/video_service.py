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
                color=(18, 18, 18),
                duration=duration
            )

            clips = [background]

            if image_path:
                image = (
                    ImageClip(image_path)
                    .with_duration(duration)
                    .resized(width=900)
                    .with_position(("center", 420))
                )
                clips.append(image)

            title = TextClip(
                text=article.title,
                font_size=58,
                color="white",
                size=(960, None),
                method="caption"
            ).with_duration(duration).with_position(("center", 120))

            source = TextClip(
                text=f"Source: {article.source}",
                font_size=36,
                color="white",
                size=(900, None),
                method="caption"
            ).with_duration(duration).with_position(("center", 1660))

            clips.append(title)
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