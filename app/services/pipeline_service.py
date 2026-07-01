from app.database.repository import ArticleRepository
from app.services.collector_service import CollectorService
from app.services.content_cleaner import ContentCleaner
from app.services.content_service import ContentService
from app.services.json_export_service import JsonExportService
from app.services.ranking_service import RankingService
from app.services.summary_service import SummaryService
from app.services.script_service import ScriptService
from app.utils.logger import get_logger
from app.services.audio_service import AudioService

class PipelineService:

    def __init__(self):
        self.logger = get_logger(__name__)

        self.collector = CollectorService()
        self.repository = ArticleRepository()
        self.ranking = RankingService()
        self.content = ContentService()
        self.cleaner = ContentCleaner()
        self.summary = SummaryService()
        self.script = ScriptService()
        self.json_export = JsonExportService()
        self.audio = AudioService()

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

        print("\n🔥 오늘의 TOP 1 뉴스 JSON 생성\n")

        for index, article in enumerate(ranked_articles[:1], start=1):
            print("=" * 80)
            print(f"{index}. [{article.score}점]")
            print(article.title)
            print(article.source)
            print(article.link)

            if not article.content:
                self.logger.info(f"본문 추출 시작 : {article.title}")
                article.content = self.content.extract_content(article.link)
                article.status = "CONTENT_DONE"
            else:
                self.logger.info(f"본문 추출 생략 : {article.title}")

            if article.content and not article.cleaned_content:
                self.logger.info(f"본문 정제 시작 : {article.title}")
                article.cleaned_content = self.cleaner.clean(article.content)
                article.status = "CLEANED"
            else:
                self.logger.info(f"본문 정제 생략 : {article.title}")

            if article.cleaned_content and not article.summary:
                self.logger.info(f"요약 생성 시작 : {article.title}")
                article.summary = self.summary.summarize(article)

                if article.summary:
                    article.status = "SUMMARY_DONE"
            else:
                self.logger.info(f"요약 생성 생략 : {article.title}")

            if article.summary and not article.script:
                self.logger.info(f"대본 생성 시작 : {article.title}")
                article.script = self.script.create_script(article)

                if article.script:
                    article.status = "SCRIPT_DONE"
            else:
                self.logger.info(f"대본 생성 생략 : {article.title}")

            json_path = self.json_export.export_article(article)
            audio_path = self.audio.create_audio(article)

            print("\nMP3 생성:")
            print(audio_path)
            
            article.status = "JSON_DONE"
            self.repository.update_article(article)

            print("\n요약:")
            print(article.summary)

            print("\n30초 쇼츠 대본:")
            print(article.script)

            print("\nJSON 저장 위치:")
            print(json_path)

        self.repository.close()

        self.logger.info("========== Pipeline 종료 ==========")