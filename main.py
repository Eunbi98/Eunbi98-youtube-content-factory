from app.services.collector_service import CollectorService
from app.database.repository import ArticleRepository
from app.services.ranking_service import RankingService
from app.services.content_service import ContentService
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():

    logger.info("========== 프로그램 시작 ==========")

    # 뉴스 수집
    collector_service = CollectorService()
    articles = collector_service.collect_all()

    logger.info(f"수집 기사 수 : {len(articles)}")

    # DB 저장
    repository = ArticleRepository()

    saved_count = 0

    for article in articles:
        if repository.save(article):
            saved_count += 1

    repository.close()

    logger.info(f"새로 저장한 기사 수 : {saved_count}")

    # 랭킹 계산
    ranking_service = RankingService()

    ranked_articles = ranking_service.rank(articles)

    # 본문 추출 서비스
    content_service = ContentService()

    print("\n==============================")
    print("🔥 오늘의 TOP 5 뉴스")
    print("==============================\n")

    for idx, (score, article) in enumerate(ranked_articles[:5], start=1):

        print(f"{idx}. [{score}점]")
        print(article.title)
        print(article.source)
        print(article.link)

        print("\n본문 추출 중...\n")

        content = content_service.extract_content(article.link)

        print(f"본문 길이 : {len(content)} 글자\n")

        print("-" * 80)

    logger.info("========== 프로그램 종료 ==========")


if __name__ == "__main__":
    main()