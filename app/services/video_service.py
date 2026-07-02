from app.video.shorts_engine import ShortsEngine
from app.video.template_loader import TemplateLoader
from config.settings import VIDEO_TEMPLATE_NAME


class VideoService:
    def __init__(self):
        self.template_loader = TemplateLoader()

    def create_video(
        self,
        article,
        image_path: str | None,
        audio_path: str | None
    ) -> str | None:
        template = self.template_loader.load(VIDEO_TEMPLATE_NAME)

        engine = ShortsEngine(template=template)

        return engine.render(
            article=article,
            image_path=image_path,
            audio_path=audio_path
        )