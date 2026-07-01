import json
from pathlib import Path


class SourceManager:

    def __init__(self, source_file: str = "sources/interesting_sources.json"):
        self.source_file = Path(source_file)

    def load_sources(self) -> list[dict]:
        if not self.source_file.exists():
            raise FileNotFoundError(
                f"소스 파일을 찾을 수 없습니다: {self.source_file}"
            )

        with open(self.source_file, "r", encoding="utf-8") as f:
            sources = json.load(f)

        return sources

    def get_rss_sources(self) -> list[dict]:
        sources = self.load_sources()

        rss_sources = [
            source for source in sources
            if source.get("type") == "rss"
        ]

        rss_sources.sort(
            key=lambda source: source.get("priority", 0),
            reverse=True
        )

        return rss_sources