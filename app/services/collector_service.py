from app.collectors.bbc import BBCCollector
from app.collectors.techcrunch import TechCrunchCollector


class CollectorService:

    def __init__(self):

        self.collectors = [
            BBCCollector(),
            TechCrunchCollector()
        ]

    def collect_all(self):

        articles = []

        for collector in self.collectors:
            articles.extend(collector.collect())

        return articles