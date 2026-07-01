from app.database.repository import ArticleRepository
from app.services.candidate_filter import CandidateFilter
from app.services.collector_service import CollectorService
from app.services.content_cleaner import ContentCleaner
from app.services.content_service import ContentService
from app.services.image_service import ImageService
from app.services.json_export_service import JsonExportService
from app.services.producer_service import ProducerService
from app.utils.logger import get_logger


class PipelineService:
    def __init__(self):
        self.logger = get_logger(__name__)

        self.collector = CollectorService()
        self.repository = ArticleRepository()

        self.content = ContentService()
        self.cleaner = ContentCleaner()
        self.candidate_filter = CandidateFilter()
        self.producer = ProducerService()

        self.json_export = JsonExportService()
        self.image = ImageService()

        self.enable_media_generation = False

    def run(self):
        self.logger.info("========== Pipeline 시작 ==========")

        collected_articles = self.collector.collect_all()
        self.logger.info(f"수집 기사 수 : {len(collected_articles)}")

        saved_count = 0

        for article in collected_articles:
            if self.repository.save(article):
                saved_count += 1

        self.logger.info(f"신규 저장 기사 수 : {saved_count}")

        articles = self.repository.get_unprocessed(limit=10)
        self.logger.info(f"처리 대상 기사 수 : {len(articles)}")

        if not articles:
            self.logger.info("처리할 기사가 없습니다.")
            self.repository.close()
            return

        for article in articles:
            if not article.content:
                self.logger.info(f"본문 추출 : {article.title}")
                article.content = self.content.extract_content(article.link)
                article.status = "CONTENT_DONE"
            else:
                self.logger.info(f"본문 추출 생략 : {article.title}")

            if article.content and not article.cleaned_content:
                self.logger.info(f"본문 정제 : {article.title}")
                article.cleaned_content = self.cleaner.clean(article.content)
                article.status = "CLEANED"
            else:
                self.logger.info(f"본문 정제 생략 : {article.title}")

            self.repository.update_article(article)

        candidates = self.candidate_filter.filter(articles, limit=5)
        self.logger.info(f"후보 기사 수 : {len(candidates)}")

        print("\n🎬 AI Producer 후보 기사\n")

        for index, article in enumerate(candidates, start=1):
            print("=" * 80)
            print(f"{index}. 후보 점수 [{article.score}점]")
            print(article.title)
            print(article.source)
            print(article.link)

        selected_article = candidates[0]

        print("\n🏆 AI Producer 평가 대상\n")
        print(selected_article.title)

        self.logger.info(f"AI Producer 평가 시작 : {selected_article.title}")
        producer_result = self.producer.produce(selected_article)

        selected_article.score = int(producer_result.get("score", 0))
        selected_article.summary = producer_result.get("summary", "")
        selected_article.script = producer_result.get("script", "")
        selected_article.thumbnail = producer_result.get("thumbnail_text", "")

        if selected_article.script:
            selected_article.status = "PRODUCER_DONE"

        print("\nAI Producer 결과")
        print(f"점수: {selected_article.score}")
        print(f"카테고리: {producer_result.get('category', '')}")
        print(f"이유: {producer_result.get('reason', '')}")
        print(f"훅: {producer_result.get('hook', '')}")
        print(f"제목: {producer_result.get('youtube_title', '')}")
        print(f"썸네일: {producer_result.get('thumbnail_text', '')}")

        json_path = self.json_export.export_article(selected_article)
        print("\nJSON 생성")
        print(json_path)

        image_path = self.image.download_image(selected_article)
        print("\n대표 이미지")
        print(image_path)

        self.repository.update_article(selected_article)
        self.repository.close()

        self.logger.info("========== Pipeline 종료 ==========")