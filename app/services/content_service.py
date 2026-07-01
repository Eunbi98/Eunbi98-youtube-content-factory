from newspaper import Article


class ContentService:

    def extract_content(self, url: str) -> str:
        """
        기사 URL에서 본문을 추출한다.
        실패하면 빈 문자열을 반환한다.
        """

        try:
            article = Article(url)

            article.download()
            article.parse()

            return article.text

        except Exception as e:
            print(f"본문 추출 실패 : {url}")
            print(e)

            return ""