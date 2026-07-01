class CandidateFilter:

    def filter(self, articles, limit=5):
        scored_articles = []

        for article in articles:
            score = self._calculate_candidate_score(article)
            scored_articles.append((score, article))

        scored_articles.sort(
            key=lambda item: item[0],
            reverse=True
        )

        return [
            article for score, article in scored_articles[:limit]
        ]

    def _calculate_candidate_score(self, article):
        score = 0

        title = article.title or ""
        content = article.content or ""
        source = article.source or ""

        if article.link:
            score += 10

        if 30 <= len(title) <= 120:
            score += 10

        if len(content) >= 1000:
            score += 10

        if source == "NASA":
            score += 20

        if source == "Live Science":
            score += 15

        if source == "ScienceDaily":
            score += 12

        if source == "Smithsonian Magazine":
            score += 12

        interest_keywords = [
            "mystery",
            "strange",
            "rare",
            "discovered",
            "reveals",
            "ancient",
            "space",
            "planet",
            "animal",
            "robot",
            "universe",
            "record",
            "hidden",
            "secret",
            "found",
        ]

        text = f"{title} {content}".lower()

        for keyword in interest_keywords:
            if keyword in text:
                score += 5

        article.score = score

        return score