from app.database.repository import ArticleRepository
from app.services.collector_service import CollectorService
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

    def run(self):
        self.logger.info("========== Pipeline 시작 ==========")

        # 1. 뉴스 수집
        collected_articles = self.collector.collect_all()
        self.logger.info(f"수집 기사 수 : {len(collected_articles)}")

        # 2. DB 저장
        saved_count = 0

        for article in collected_articles:
            if self.repository.save(article):
                saved_count += 1

        self.logger.info(f"신규 저장 기사 수 : {saved_count}")

        # 3. 아직 처리되지 않은 기사 가져오기
        articles = self.repository.get_unprocessed(limit=10)
        self.logger.info(f"처리 대상 기사 수 : {len(articles)}")

        # 4. 랭킹 계산
        ranked_articles = self.ranking.rank(articles)

        print("\n🔥 오늘의 TOP 5 뉴스\n")

        # 5. 상위 5개 기사 본문 추출 후 DB 업데이트
        for index, article in enumerate(ranked_articles[:5], start=1):
            print("=" * 80)
            print(f"{index}. [{article.score}점]")
            print(article.title)
            print(article.source)
            print(article.link)

            article.content = self.content.extract_content(article.link)
            article.status = "PROCESSED"

            self.repository.update_article(article)

            print(f"\n본문 길이 : {len(article.content)} 글자")

        self.repository.close()

        self.logger.info("========== Pipeline 종료 ==========")