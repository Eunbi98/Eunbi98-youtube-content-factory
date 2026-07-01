from app.services.collector_service import CollectorService
from app.utils.logger import get_logger


logger = get_logger(__name__)


def main():

    logger.info("프로그램 시작")

    service = CollectorService()

    articles = service.collect_all()

    logger.info(f"{len(articles)}개의 뉴스 수집 완료")

    print()

    for article in articles[:10]:
        print(article.title)

    logger.info("프로그램 종료")


if __name__ == "__main__":
    main()