from pathlib import Path

from moviepy import (
    AudioFileClip,
    ColorClip,
    CompositeVideoClip,
    ImageClip,
    TextClip
)


class VideoService:

    def __init__(self):
        self.output_dir = Path("output/video")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.width = 1080
        self.height = 1920

    def create_video(self, article, image_path: str, audio_path: str) -> str | None:
        if not audio_path:
            return None

        output_path = self.output_dir / "news.mp4"

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
            fps=30,
            codec="libx264",
            audio_codec="aac"
        )

        audio.close()
        video.close()

        return str(output_path)