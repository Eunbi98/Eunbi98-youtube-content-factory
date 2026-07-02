from app.collectors.bbc import BBCCollector
from app.collectors.nasa import NASACollector
from app.collectors.techcrunch import TechCrunchCollector
from app.services.source_manager import SourceManager
from app.utils.logger import get_logger


class CollectorService:
    def __init__(self):
        self.logger = get_logger(__name__)
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
            else:
                self.logger.warning(f"등록되지 않은 Collector: {collector_name}")

    def collect_all(self):
        articles = []

        for collector in self.collectors:
            try:
                collected = collector.collect()
                articles.extend(collected)
                self.logger.info(
                    f"{collector.__class__.__name__} 수집 완료: {len(collected)}건"
                )

            except Exception as e:
                self.logger.error(
                    f"{collector.__class__.__name__} 수집 실패: {e}"
                )

        return articles