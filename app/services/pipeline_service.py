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

        producer_targets = candidates[:3]
        produced_articles = []

        print("\n🤖 AI Producer 평가 시작\n")

        for index, article in enumerate(producer_targets, start=1):
            print("=" * 80)
            print(f"{index}. AI 평가 대상")
            print(article.title)

            self.logger.info(f"AI Producer 평가 시작 : {article.title}")
            producer_result = self.producer.produce(article)

            article.score = int(producer_result.get("score", 0))

            summary = producer_result.get("summary", "")
            script = producer_result.get("script", "")
            thumbnail_text = producer_result.get("thumbnail_text", "")

            if isinstance(summary, list):
                summary = " ".join(str(item) for item in summary)

            if isinstance(script, list):
                script = "\n".join(str(item) for item in script)

            if isinstance(thumbnail_text, list):
                thumbnail_text = " ".join(str(item) for item in thumbnail_text)

            article.summary = str(summary)
            article.script = str(script)
            article.thumbnail = str(thumbnail_text)

            if article.script:
                article.status = "PRODUCER_DONE"

            produced_articles.append({
                "article": article,
                "producer_result": producer_result
            })

            print("\nAI Producer 결과")
            print(f"점수: {article.score}")
            print(f"카테고리: {producer_result.get('category', '')}")
            print(f"이유: {producer_result.get('reason', '')}")
            print(f"훅: {producer_result.get('hook', '')}")
            print(f"제목: {producer_result.get('youtube_title', '')}")
            print(f"썸네일: {producer_result.get('thumbnail_text', '')}")

            self.repository.update_article(article)

        produced_articles.sort(
            key=lambda item: item["article"].score,
            reverse=True
        )

        selected_item = produced_articles[0]
        selected_article = selected_item["article"]
        selected_result = selected_item["producer_result"]

        print("\n🏆 최종 선택 기사\n")
        print(f"점수: {selected_article.score}")
        print(selected_article.title)
        print(selected_article.source)
        print(selected_article.link)
        print(f"선택 이유: {selected_result.get('reason', '')}")

        json_path = self.json_export.export_article(selected_article)
        print("\nJSON 생성")
        print(json_path)

        image_path = self.image.download_image(selected_article)
        print("\n대표 이미지")
        print(image_path)

        selected_article.status = "SELECTED"
        self.repository.update_article(selected_article)

        self.repository.close()

        self.logger.info("========== Pipeline 종료 ==========")