from abc import ABC, abstractmethod
from app.models.article import Article


class BaseCollector(ABC):

    @abstractmethod
    def collect(self) -> list[Article]:
        """
        뉴스를 수집해서 Article 리스트를 반환한다.
        """
        pass