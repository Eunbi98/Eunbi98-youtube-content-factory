from app.collectors.bbc import BBCCollector
from app.collectors.techcrunch import TechCrunchCollector
from app.services.source_manager import SourceManager
from app.collectors.nasa import NASACollector

class CollectorService:

    def __init__(self):

        self.source_manager = SourceManager()

        available_collectors = {
            "BBCCollector": BBCCollector,
            "TechCrunchCollector": TechCrunchCollector,
            "NASACollector": NASACollector,
        }

        self.collectors = []

        for source in self.source_manager.load_sources():

            if not source.get("enabled", True):
                continue

            collector_name = source.get("collector")

            collector_class = available_collectors.get(collector_name)

            if collector_class:
                self.collectors.append(collector_class())

    def collect_all(self):

        articles = []

        for collector in self.collectors:

            try:
                articles.extend(collector.collect())

            except Exception as e:
                print(f"{collector.__class__.__name__} 실패 : {e}")

        return articles