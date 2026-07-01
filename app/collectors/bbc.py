import os
import feedparser
from dotenv import load_dotenv

from app.models.article import Article
from app.collectors.base import BaseCollector

load_dotenv()


class BBCCollector(BaseCollector):

    def collect(self) -> list[Article]:

        rss_url = os.getenv("BBC_RSS")

        feed = feedparser.parse(rss_url)

        articles = []

        for entry in feed.entries:

            article = Article(
                title=entry.title,
                link=entry.link,
                source="BBC",
                published=entry.get("published", "")
            )

            articles.append(article)

        return articles