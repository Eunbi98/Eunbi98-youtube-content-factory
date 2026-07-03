from app.database.repository import ArticleRepository
from app.services.audio_service import AudioService
from app.services.candidate_filter import CandidateFilter
from app.services.collector_service import CollectorService
from app.services.content_cleaner import ContentCleaner
from app.services.content_planner_service import ContentPlannerService
from app.services.content_service import ContentService
from app.services.final_output_guard import FinalOutputGuard
from app.services.image_service import ImageService
from app.services.json_export_service import JsonExportService
from app.services.scene_image_service import SceneImageService
from app.services.subtitle_service import SubtitleService
from app.services.video_service import VideoService
from app.utils.logger import get_logger
from config.settings import (
    AI_TARGET_COUNT,
    CANDIDATE_LIMIT,
    ENABLE_AUDIO,
    ENABLE_IMAGE_DOWNLOAD,
    ENABLE_SCENE_IMAGES,
    ENABLE_SUBTITLE,
    ENABLE_VIDEO,
    PROCESS_LIMIT,
)


class PipelineService:
    def __init__(self):
        self.logger = get_logger(__name__)

        self.collector = CollectorService()
        self.repository = ArticleRepository()

        self.content = ContentService()
        self.cleaner = ContentCleaner()
        self.candidate_filter = CandidateFilter()
        self.content_planner = ContentPlannerService()
        self.final_output_guard = FinalOutputGuard()

        self.json_export = JsonExportService()
        self.image = ImageService()
        self.scene_image = SceneImageService()
        self.audio = AudioService()
        self.subtitle = SubtitleService()
        self.video = VideoService()

    def run(self):
        self.logger.info("========== Pipeline 시작 ==========")

        try:
            self._collect_articles()
            articles = self._prepare_articles()

            if not articles:
                self.logger.info("처리할 기사가 없습니다.")
                return

            candidates = self._select_candidates(articles)

            if not candidates:
                self.logger.info("후보 기사가 없습니다.")
                return

            planned_articles = self._plan_contents(candidates)

            if not planned_articles:
                self.logger.info("AI 기획 결과가 없습니다.")
                return

            selected_article = self._select_best_article(planned_articles)
            self._create_outputs(selected_article)

            selected_article.status = "DONE"
            self.repository.update_article(selected_article)

            self.logger.info("========== Pipeline 완료 ==========")

        finally:
            self.repository.close()

    def _collect_articles(self):
        collected_articles = self.collector.collect_all()
        self.logger.info(f"수집 기사 수: {len(collected_articles)}")

        saved_count = 0

        for article in collected_articles:
            if self.repository.save(article):
                saved_count += 1

        self.logger.info(f"신규 저장 기사 수: {saved_count}")

    def _prepare_articles(self):
        articles = self.repository.get_unprocessed(limit=PROCESS_LIMIT)
        self.logger.info(f"처리 대상 기사 수: {len(articles)}")

        for article in articles:
            try:
                if not article.content:
                    self.logger.info(f"본문 추출: {article.title}")
                    article.content = self.content.extract_content(article.link)
                    article.status = "CONTENT_DONE"

                if article.content and not article.cleaned_content:
                    self.logger.info(f"본문 정제: {article.title}")
                    article.cleaned_content = self.cleaner.clean(article.content)
                    article.status = "CLEANED"

                self.repository.update_article(article)

            except Exception as e:
                self.logger.error(f"본문 처리 실패: {article.title} / {e}")
                article.status = "FAILED"
                self.repository.update_article(article)

        return articles

    def _select_candidates(self, articles):
        candidates = self.candidate_filter.filter(
            articles,
            limit=CANDIDATE_LIMIT
        )

        self.logger.info(f"후보 기사 수: {len(candidates)}")

        print("\n콘텐츠 후보 기사\n")

        for index, article in enumerate(candidates, start=1):
            print("=" * 80)
            print(f"{index}. 후보 점수 [{article.score}]")
            print(article.title)
            print(article.source)
            print(article.link)

        return candidates

    def _plan_contents(self, candidates):
        planner_targets = candidates[:AI_TARGET_COUNT]
        planned_articles = []

        print("\nContent Planner 평가 시작\n")

        for index, article in enumerate(planner_targets, start=1):
            try:
                print("=" * 80)
                print(f"{index}. 기획 대상")
                print(article.title)

                self.logger.info(f"Content Planner 평가 시작: {article.title}")
                plan_result = self.content_planner.plan(article)

                article.score = int(plan_result.get("score", 0))
                article.summary = self._to_text(plan_result.get("summary", ""))
                article.script = self._to_text(plan_result.get("script", ""))
                article.thumbnail = self._to_text(
                    plan_result.get("thumbnail_text", "")
                )
                article.hashtags = plan_result.get("hashtags", [])
                article.scenes = plan_result.get("scenes", [])

                if article.script:
                    article.status = "PLANNED"
                else:
                    article.status = "FAILED"

                self.repository.update_article(article)

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
                print(f"장면 수: {len(article.scenes)}")

            except Exception as e:
                self.logger.error(f"AI 기획 실패: {article.title} / {e}")
                article.status = "FAILED"
                self.repository.update_article(article)

        return planned_articles

    def _select_best_article(self, planned_articles):
        planned_articles.sort(
            key=lambda item: item["article"].score,
            reverse=True
        )

        selected_item = planned_articles[0]
        selected_article = selected_item["article"]
        selected_result = selected_item["plan_result"]

        print("\n최종 선택 콘텐츠\n")
        print(f"점수: {selected_article.score}")
        print(selected_article.title)
        print(selected_article.source)
        print(selected_article.link)
        print(f"선택 이유: {selected_result.get('reason', '')}")

        selected_article.status = "SELECTED"
        self.repository.update_article(selected_article)

        return selected_article

    def _create_outputs(self, article):
        diagnostics = self.final_output_guard.enforce_article(article)
        print("\nFinal Output Guard")
        print(f"final_title: {diagnostics['final_title']}")
        print(f"final_script_preview: {diagnostics['final_script_preview']}")
        print(f"final_tts_preview: {diagnostics['final_tts_preview']}")
        print(f"korean_ratio: {diagnostics['korean_ratio']:.2f}")
        print(f"english_ratio: {diagnostics['english_ratio']:.2f}")

        json_path = self.json_export.export_article(article)
        print("\nJSON 생성")
        print(json_path)

        image_path = None
        image_paths = []
        audio_path = None

        if ENABLE_IMAGE_DOWNLOAD:
            image_path = self.image.download_image(article)
            print("\n대표 이미지 저장")
            print(image_path)

        if ENABLE_SCENE_IMAGES:
            image_paths = self.scene_image.download_scene_images(
                article=article,
                fallback_image_path=image_path
            )
            print("\n장면 이미지 저장")
            for path in image_paths:
                print(path)

        if ENABLE_AUDIO:
            audio_path = self.audio.create_audio(article)
            print("\n음성 생성")
            print(audio_path)

        if ENABLE_SUBTITLE:
            subtitle_path = self.subtitle.create_srt(article)
            print("\n자막 생성")
            print(subtitle_path)

        if ENABLE_VIDEO:
            video_path = self.video.create_video(
                article=article,
                image_path=image_path,
                image_paths=image_paths,
                audio_path=audio_path
            )
            print("\n영상 생성")
            print(video_path)

    def _to_text(self, value):
        if isinstance(value, list):
            return "\n".join(str(item) for item in value)

        return str(value)
