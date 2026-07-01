from app.database.repository import ArticleRepository
from app.models import article
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
        articles = self.collector.collect_all()

        self.logger.info(f"수집 기사 수 : {len(articles)}")

        # 2. DB 저장
        saved = 0

        for article in articles:

            if self.repository.save(article):
                saved += 1

        self.logger.info(f"신규 저장 기사 : {saved}")

        # 3. 랭킹
        ranked = self.ranking.rank(articles)

        print("\n🔥 오늘의 TOP 5 뉴스\n")

        # 4. 본문 추출
        for index, article in enumerate(ranked[:5], start=1):

            print(f"{index}. [{article.score}점]")
            print(article.title)
            print(article.source)
            print(article.link)

            content = self.content.extract_content(article.link)

            print(f"\n본문 길이 : {len(content)} 글자")

        self.repository.close()

        self.logger.info("========== Pipeline 종료 ==========")