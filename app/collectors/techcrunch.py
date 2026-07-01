import os
import feedparser
from dotenv import load_dotenv

from app.collectors.base import BaseCollector
from app.models.article import Article

load_dotenv()


class TechCrunchCollector(BaseCollector):

    def collect(self):

        rss = os.getenv("TECHCRUNCH_RSS")

        feed = feedparser.parse(rss)

        articles = []

        for entry in feed.entries:

            article = Article(
                title=entry.title,
                link=entry.link,
                source="TechCrunch",
                published=entry.get("published", "")
            )

            articles.append(article)

        return articles