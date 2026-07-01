from app.services.collector_service import CollectorService
from app.database.repository import ArticleRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


def main():

    logger.info("프로그램 시작")

    service = CollectorService()
    repository = ArticleRepository()

    articles = service.collect_all()

    saved = 0

    for article in articles:

        if repository.save(article):
            saved += 1

    logger.info(f"수집 기사 수 : {len(articles)}")
    logger.info(f"새로 저장한 기사 : {saved}")

    repository.close()

    logger.info("프로그램 종료")


if __name__ == "__main__":
    main()