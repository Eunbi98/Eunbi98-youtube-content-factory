import json
from pathlib import Path
from datetime import datetime


class JsonExportService:
    def __init__(self):
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)

    def export_article(self, article) -> str:
        data = {
            "title": article.title,
            "source": article.source,
            "link": article.link,
            "score": article.score,
            "summary": article.summary,
            "script": article.script,
            "thumbnail": article.thumbnail,
            "hashtags": article.hashtags,
            "created_at": datetime.now().isoformat()
        }

        filename = self._make_filename(article.title)
        file_path = self.output_dir / filename

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        return str(file_path)

    def _make_filename(self, title: str) -> str:
        safe_title = "".join(
            char for char in title[:40]
            if char.isalnum() or char in (" ", "_", "-")
        ).strip()

        safe_title = safe_title.replace(" ", "_")

        if not safe_title:
            safe_title = "news_item"

        return f"{safe_title}.json"