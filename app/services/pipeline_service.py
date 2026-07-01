from app.database.repository import ArticleRepository
from app.services.collector_service import CollectorService
from app.services.content_cleaner import ContentCleaner
from app.services.content_service import ContentService
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

    def run(self):
        self.logger.info("========== Pipeline 시작 ==========")

        # 1. 뉴스 수집
        collected_articles = self.collector.collect_all()
        self.logger.info(f"수집 기사 수 : {len(collected_articles)}")

        # 2. 신규 기사 DB 저장
        saved_count = 0

        for article in collected_articles:
            if self.repository.save(article):
                saved_count += 1

        self.logger.info(f"신규 저장 기사 수 : {saved_count}")

        # 3. 아직 처리할 기사 가져오기
        articles = self.repository.get_unprocessed(limit=10)
        self.logger.info(f"처리 대상 기사 수 : {len(articles)}")

        if not articles:
            self.logger.info("처리할 기사가 없습니다.")
            self.repository.close()
            return

        # 4. 랭킹 계산
        ranked_articles = self.ranking.rank(articles)

        print("\n🔥 오늘의 TOP 5 뉴스\n")

        # 5. 상위 기사 처리
        for index, article in enumerate(ranked_articles[:5], start=1):
            print("=" * 80)
            print(f"{index}. [{article.score}점]")
            print(article.title)
            print(article.source)
            print(article.link)

            # 본문이 없을 때만 추출
            if not article.content:
                self.logger.info(f"본문 추출 시작 : {article.title}")
                article.content = self.content.extract_content(article.link)
                article.status = "CONTENT_DONE"
            else:
                self.logger.info(f"본문 추출 생략 : {article.title}")

            # 정제 본문이 없을 때만 정제
            if article.content and not article.cleaned_content:
                self.logger.info(f"본문 정제 시작 : {article.title}")
                article.cleaned_content = self.cleaner.clean(article.content)
                article.status = "CLEANED"
            else:
                self.logger.info(f"본문 정제 생략 : {article.title}")

            self.repository.update_article(article)

            print(f"\n원문 길이 : {len(article.content)} 글자")
            print(f"정제 후 길이 : {len(article.cleaned_content)} 글자")

        self.repository.close()

        self.logger.info("========== Pipeline 종료 ==========")