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

        return score

    def rank(self, articles):

        ranked = []

        for article in articles:
            score = self.calculate_score(article)
            ranked.append((score, article))

        ranked.sort(key=lambda x: x[0], reverse=True)

        return ranked