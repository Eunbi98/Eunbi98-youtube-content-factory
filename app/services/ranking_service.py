class RankingService:

    KEYWORDS = {
        "OpenAI": 30,
        "ChatGPT": 30,
        "AI": 20,
        "NVIDIA": 20,
        "Tesla": 15,
        "Apple": 15,
        "Google": 15,
        "Microsoft": 10,
        "Meta": 10,
        "Amazon": 10,
        "Robot": 10,
        "SpaceX": 15,
    }

    def calculate_score(self, article):

        score = 0

        title = article.title.lower()

        for keyword, point in self.KEYWORDS.items():

            if keyword.lower() in title:
                score += point

        article.score = score

        return score

    def rank(self, articles):

        for article in articles:
            self.calculate_score(article)

        return sorted(
            articles,
            key=lambda article: article.score,
            reverse=True
        )