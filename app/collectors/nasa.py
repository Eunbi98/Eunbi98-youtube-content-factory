import feedparser

from app.collectors.base import BaseCollector
from app.models.article import Article


class NASACollector(BaseCollector):

    RSS_URL = "https://www.nasa.gov/rss/dyn/breaking_news.rss"

    def collect(self) -> list[Article]:
        feed = feedparser.parse(self.RSS_URL)

        articles = []

        for entry in feed.entries:
            article = Article(
                title=entry.title,
                link=entry.link,
                source="NASA",
                published=entry.get("published", "")
            )

            articles.append(article)

        return articles