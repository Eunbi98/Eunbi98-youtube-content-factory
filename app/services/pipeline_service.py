from app.database.repository import ArticleRepository
from app.services.candidate_filter import CandidateFilter
from app.services.collector_service import CollectorService
from app.services.content_cleaner import ContentCleaner
from app.services.content_planner_service import ContentPlannerService
from app.services.content_service import ContentService
from app.services.image_service import ImageService
from app.services.json_export_service import JsonExportService
from app.utils.logger import get_logger


class PipelineService:
    def __init__(self):
        self.logger = get_logger(__name__)

        self.collector = CollectorService()
        self.repository = ArticleRepository()

        self.content = ContentService()
        self.cleaner = ContentCleaner()
        self.candidate_filter = CandidateFilter()
        self.content_planner = ContentPlannerService()

        self.json_export = JsonExportService()
        self.image = ImageService()

    def run(self):
        self.logger.info("========== Pipeline 시작 ==========")

        collected_articles = self.collector.collect_all()
        self.logger.info(f"수집 기사 수 : {len(collected_articles)}")

        saved_count = 0

        for article in collected_articles:
            if self.repository.save(article):
                saved_count += 1

        self.logger.info(f"신규 저장 기사 수 : {saved_count}")

        articles = self.repository.get_unprocessed(limit=10)
        self.logger.info(f"처리 대상 기사 수 : {len(articles)}")

        if not articles:
            self.logger.info("처리할 기사가 없습니다.")
            self.repository.close()
            return

        for article in articles:
            if not article.content:
                self.logger.info(f"본문 추출 : {article.title}")
                article.content = self.content.extract_content(article.link)
                article.status = "CONTENT_DONE"
            else:
                self.logger.info(f"본문 추출 생략 : {article.title}")

            if article.content and not article.cleaned_content:
                self.logger.info(f"본문 정제 : {article.title}")
                article.cleaned_content = self.cleaner.clean(article.content)
                article.status = "CLEANED"
            else:
                self.logger.info(f"본문 정제 생략 : {article.title}")

            self.repository.update_article(article)

        candidates = self.candidate_filter.filter(articles, limit=5)
        self.logger.info(f"후보 기사 수 : {len(candidates)}")

        print("\n🎬 콘텐츠 후보 기사\n")

        for index, article in enumerate(candidates, start=1):
            print("=" * 80)
            print(f"{index}. 후보 점수 [{article.score}점]")
            print(article.title)
            print(article.source)
            print(article.link)

        planner_targets = candidates[:3]
        planned_articles = []

        print("\n🤖 Content Planner 평가 시작\n")

        for index, article in enumerate(planner_targets, start=1):
            print("=" * 80)
            print(f"{index}. 기획 대상")
            print(article.title)

            self.logger.info(f"Content Planner 평가 시작 : {article.title}")
            plan_result = self.content_planner.plan(article)

            article.score = int(plan_result.get("score", 0))
            article.summary = self._to_text(plan_result.get("summary", ""))
            article.script = self._to_text(plan_result.get("script", ""))
            article.thumbnail = self._to_text(plan_result.get("thumbnail_text", ""))
            article.hashtags = plan_result.get("hashtags", [])

            if article.script:
                article.status = "PLANNED"

            planned_articles.append({
                "article": article,
                "plan_result": plan_result
            })

            print("\nContent Planner 결과")
            print(f"점수: {article.score}")
            print(f"카테고리: {plan_result.get('category', '')}")
            print(f"감정: {plan_result.get('emotion', '')}")
            print(f"이유: {plan_result.get('reason', '')}")
            print(f"핵심 주제: {plan_result.get('core_topic', '')}")
            print(f"훅: {plan_result.get('hook', '')}")
            print(f"제목: {plan_result.get('youtube_title', '')}")
            print(f"썸네일: {plan_result.get('thumbnail_text', '')}")

            self.repository.update_article(article)

        planned_articles.sort(
            key=lambda item: item["article"].score,
            reverse=True
        )

        selected_item = planned_articles[0]
        selected_article = selected_item["article"]
        selected_result = selected_item["plan_result"]

        print("\n🏆 최종 선택 콘텐츠\n")
        print(f"점수: {selected_article.score}")
        print(selected_article.title)
        print(selected_article.source)
        print(selected_article.link)
        print(f"선택 이유: {selected_result.get('reason', '')}")

        json_path = self.json_export.export_article(selected_article)
        print("\nJSON 생성")
        print(json_path)

        image_path = self.image.download_image(selected_article)
        print("\n대표 이미지")
        print(image_path)

        selected_article.status = "SELECTED"
        self.repository.update_article(selected_article)

        self.repository.close()

        self.logger.info("========== Pipeline 종료 ==========")

    def _to_text(self, value):
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)

        return str(value)