from app.database.repository import ArticleRepository
from app.services.collector_service import CollectorService
from app.services.content_cleaner import ContentCleaner
from app.services.content_service import ContentService
from app.services.image_service import ImageService
from app.services.json_export_service import JsonExportService
from app.services.producer_service import ProducerService
from app.services.ranking_service import RankingService
from app.utils.logger import get_logger


class PipelineService:
    def __init__(self):
        self.logger = get_logger(__name__)

        self.collector = CollectorService()
        self.repository = ArticleRepository()
        self.ranking = RankingService()

        self.content = ContentService()
        self.cleaner = ContentCleaner()
        self.producer = ProducerService()

        self.json_export = JsonExportService()
        self.image = ImageService()

        # 개발 중 임시 비활성화
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

        ranked_articles = self.ranking.rank(articles)

        print("\n🎬 AI Producer 영상 후보 평가\n")

        for index, article in enumerate(ranked_articles[:1], start=1):
            print("=" * 80)
            print(f"{index}. 기존 점수 [{article.score}점]")
            print(article.title)
            print(article.source)
            print(article.link)

            if not article.content:
                self.logger.info(f"본문 추출 : {article.title}")
                article.content = self.content.extract_content(article.link)
                article.status = "CONTENT_DONE"
            else:
                self.logger.info("본문 추출 생략")

            if article.content and not article.cleaned_content:
                self.logger.info(f"본문 정제 : {article.title}")
                article.cleaned_content = self.cleaner.clean(article.content)
                article.status = "CLEANED"
            else:
                self.logger.info("본문 정제 생략")

            self.logger.info(f"AI Producer 평가 시작 : {article.title}")
            producer_result = self.producer.produce(article)

            article.score = int(producer_result.get("score", 0))
            article.summary = producer_result.get("summary", "")
            article.script = producer_result.get("script", "")
            article.thumbnail = producer_result.get("thumbnail_text", "")

            if article.script:
                article.status = "PRODUCER_DONE"

            print("\nAI Producer 결과")
            print(f"점수: {article.score}")
            print(f"카테고리: {producer_result.get('category', '')}")
            print(f"이유: {producer_result.get('reason', '')}")
            print(f"훅: {producer_result.get('hook', '')}")
            print(f"제목: {producer_result.get('youtube_title', '')}")
            print(f"썸네일: {producer_result.get('thumbnail_text', '')}")

            json_path = self.json_export.export_article(article)
            print("\nJSON 생성")
            print(json_path)

            image_path = self.image.download_image(article)
            print("\n대표 이미지")
            print(image_path)

            if self.enable_media_generation:
                # 나중에 영상 생성 테스트를 다시 켤 때 이 안에
                # AudioService, SubtitleService, VideoService를 연결합니다.
                pass

            self.repository.update_article(article)

            print("\n요약")
            print(article.summary)

            print("\n쇼츠 대본")
            print(article.script)

        self.repository.close()

        self.logger.info("========== Pipeline 종료 ==========")