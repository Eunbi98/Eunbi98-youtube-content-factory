from __future__ import annotations

import logging

from app.story import KoreanLanguageGuard, StoryDirector, normalize_english_terms
from app.video.title_generator import VideoTitleGenerator


logger = logging.getLogger(__name__)


class FinalOutputGuard:
    def __init__(self) -> None:
        self.story_director = StoryDirector()
        self.language_guard = KoreanLanguageGuard()
        self.title_generator = VideoTitleGenerator()

    def enforce_article(self, article) -> dict[str, object]:
        story_plan = self.story_director.create_story(
            title=getattr(article, "title", "") or "",
            summary=(
                getattr(article, "summary", "")
                or getattr(article, "cleaned_content", "")
                or getattr(article, "content", "")
                or getattr(article, "script", "")
            )[:1500],
            source=getattr(article, "source", "") or "",
            url=getattr(article, "link", "") or "",
        )

        original_script = normalize_english_terms(getattr(article, "script", "") or "")
        final_script = self.language_guard.ensure_korean_script(
            script=original_script,
            story_plan=story_plan,
        )

        article.script = final_script
        article.scenes = self.language_guard.sync_scenes_to_script(
            final_script,
            getattr(article, "scenes", []) or [],
        )

        final_title = self.title_generator.generate(article)
        if hasattr(article, "thumbnail"):
            article.thumbnail = final_title

        metrics = self.language_guard.inspect(final_script)
        diagnostics = {
            "final_title": final_title,
            "final_script_preview": final_script[:180],
            "final_tts_preview": final_script[:180],
            "korean_ratio": metrics["korean_ratio"],
            "english_ratio": metrics["english_ratio"],
            "script_line_count": len(final_script.splitlines()),
            "scene_count": len(article.scenes),
        }

        if not metrics["is_korean_safe"]:
            logger.warning("Final text still needs review: %s", diagnostics)

        return diagnostics
