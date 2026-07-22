from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.topic.topic_finder import (  # noqa: E402
    AutoTopicFinder,
    TopicFinderError,
)
from projects.topic.topic_models import TopicSourceItem  # noqa: E402


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)


class FakeSource:
    def __init__(self, items: list[TopicSourceItem]) -> None:
        self.items = items

    def fetch(self, *, category: str, limit: int) -> list[TopicSourceItem]:
        return self.items[:limit]


class FailingSource:
    def fetch(self, *, category: str, limit: int) -> list[TopicSourceItem]:
        raise RuntimeError("network unavailable")


class UnexpectedSource:
    def fetch(self, *, category: str, limit: int) -> list[TopicSourceItem]:
        raise AssertionError("archive mode must not fetch live news")


class CategorySource:
    items = {
        "mystery": "고대 유적에서 새로운 미스터리 암호 발견",
        "science": "과학 연구에서 새로운 생명 현상 발견",
        "history": "고대 무덤 발굴에서 새로운 역사 유물 발견",
        "space": "NASA 화성 행성 관측에서 새로운 흔적 발견",
    }

    def fetch(self, *, category: str, limit: int) -> list[TopicSourceItem]:
        return [
            TopicSourceItem(
                title=self.items[category],
                url=f"https://example.com/{category}",
                source="NASA" if category == "space" else "연합뉴스",
                published_at="2026-07-17T10:00:00+00:00",
            )
        ]


class TopicFinderTests(unittest.TestCase):
    def test_recent_repeated_topic_is_ranked_first(self) -> None:
        items = [
            TopicSourceItem(
                title="새롭게 발견된 고대 유적의 정체 밝혀졌다 - 뉴스A",
                url="https://example.com/a",
                source="뉴스A",
                published_at="2026-07-17T09:00:00+00:00",
            ),
            TopicSourceItem(
                title="새롭게 발견된 고대 유적 정체 밝혀져 - 뉴스B",
                url="https://example.com/b",
                source="뉴스B",
                published_at="2026-07-17T08:00:00+00:00",
            ),
            TopicSourceItem(
                title="심해 생물의 오래된 기록을 다시 읽는 방법 - 뉴스C",
                url="https://example.com/c",
                source="뉴스C",
                published_at="2026-07-03T08:00:00+00:00",
            ),
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="mystery", limit=2)

        self.assertEqual("hybrid", result.mode)
        self.assertIn("고대 유적", result.candidates[0].topic)
        self.assertEqual(2, result.candidates[0].source_count)
        self.assertGreater(
            result.candidates[0].score,
            result.candidates[1].score,
        )

    def test_source_failure_returns_only_preflighted_safe_candidates(self) -> None:
        result = AutoTopicFinder(
            source=FailingSource(),
            now=lambda: NOW,
        ).find(category="science", limit=10)

        self.assertEqual("fallback", result.mode)
        self.assertEqual(5, result.candidate_count)
        self.assertEqual(1, result.candidates[0].rank)
        self.assertEqual(5, result.candidates[-1].rank)
        self.assertTrue(all(item.production_ready for item in result.candidates))
        self.assertTrue(all(item.readiness_score == 100 for item in result.candidates))
        self.assertTrue(result.warnings)

    def test_partial_live_results_are_filled_from_catalog(self) -> None:
        items = [
            TopicSourceItem(
                title="화성에서 새로운 물의 흔적 발견 - 우주뉴스",
                url="https://example.com/mars",
                source="NASA",
                published_at="2026-07-17T10:00:00+00:00",
            )
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="space", limit=3)

        self.assertEqual("hybrid", result.mode)
        self.assertEqual(3, len(result.candidates))
        self.assertEqual(1, result.candidates[0].source_count)
        self.assertEqual(0, result.candidates[1].source_count)

    def test_unsupported_category_is_rejected(self) -> None:
        with self.assertRaises(TopicFinderError):
            AutoTopicFinder(
                source=FakeSource([]),
                now=lambda: NOW,
            ).find(category="crime")

    def test_existing_episode_topic_is_excluded(self) -> None:
        items = [
            TopicSourceItem(
                title="미라의 입에서 발견된 순금 혀와 고대 무덤의 비밀",
                url="https://example.com/gold-tongue",
                source="고고학뉴스",
                published_at="2026-07-17T10:00:00+00:00",
            ),
            TopicSourceItem(
                title="화성에서 발견된 미스터리 구조물의 정체",
                url="https://example.com/mars",
                source="NASA",
                published_at="2026-07-17T09:00:00+00:00",
            ),
        ]
        existing_episode = (
            "죽은 자에게 주어진 황금 혀. 고대 이집트 미라의 입에 "
            "황금 혀를 넣은 무덤이 발견됐습니다."
        )
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(
            category="mystery",
            limit=1,
            excluded_topics=[existing_episode],
        )

        self.assertIn("화성", result.candidates[0].topic)

    def test_result_is_json_serializable_shape(self) -> None:
        result = AutoTopicFinder(
            source=FailingSource(),
            now=lambda: NOW,
        ).find(category="history", limit=1)
        payload = result.to_dict()

        self.assertEqual("history", payload["category"])
        self.assertEqual(1, payload["candidate_count"])
        self.assertEqual(1, payload["candidates"][0]["rank"])

    def test_fallback_candidate_is_sorted_by_score(self) -> None:
        items = [
            TopicSourceItem(
                title="심해에서 전해진 오래된 기록",
                url="https://example.com/weak-live",
                source="지역뉴스",
                published_at="2026-06-01T10:00:00+00:00",
            )
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="mystery", limit=2)

        self.assertEqual("fallback", result.mode)
        self.assertGreaterEqual(
            result.candidates[0].score,
            result.candidates[1].score,
        )

    def test_single_untrusted_live_story_is_not_recommended(self) -> None:
        items = [
            TopicSourceItem(
                title="화성에서 새로운 물의 흔적 발견",
                url="https://example.com/unverified",
                source="우주블로그",
                published_at="2026-07-17T10:00:00+00:00",
            )
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="space", limit=2)

        self.assertEqual("fallback", result.mode)
        self.assertTrue(all(item.source_count == 0 for item in result.candidates))
        self.assertTrue(all(item.production_ready for item in result.candidates))

    def test_low_quality_translation_source_is_filtered(self) -> None:
        items = [
            TopicSourceItem(
                title="3천년 된 고대 무덤에서 새로운 유물 발견",
                url="https://example.com/translated",
                source="Vietnam.vn",
                published_at="2026-07-17T10:00:00+00:00",
            )
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="history", limit=1)

        self.assertEqual("fallback", result.mode)
        self.assertEqual(0, result.candidates[0].source_count)

    def test_archive_mode_uses_curated_topics_without_live_fetch(self) -> None:
        result = AutoTopicFinder(
            source=UnexpectedSource(),
            now=lambda: NOW,
        ).find(category="mystery", limit=3, source_mode="archive")

        self.assertEqual("archive", result.mode)
        self.assertEqual(3, result.candidate_count)
        self.assertTrue(
            all(candidate.source_count == 0 for candidate in result.candidates)
        )
        self.assertTrue(
            any(
                "Antikythera mechanism" in query
                for candidate in result.candidates
                for query in candidate.search_queries
            )
        )
        self.assertIn("미스터리 아카이브", result.candidates[0].reasons[0])

    def test_mixed_mode_keeps_trend_and_archive_quota(self) -> None:
        items = [
            TopicSourceItem(
                title="화성에서 새로운 물의 흔적 발견",
                url="https://example.com/mars-water",
                source="NASA",
                published_at="2026-07-17T10:00:00+00:00",
            ),
            TopicSourceItem(
                title="외계 행성 대기에서 생명 연구 단서 발견",
                url="https://example.com/exoplanet",
                source="Science",
                published_at="2026-07-17T09:00:00+00:00",
            ),
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="space", limit=5, source_mode="mixed")

        self.assertEqual("mixed", result.mode)
        self.assertEqual(2, sum(item.source_count > 0 for item in result.candidates))
        self.assertEqual(3, sum(item.source_count == 0 for item in result.candidates))

    def test_all_category_combines_multiple_channel_categories(self) -> None:
        result = AutoTopicFinder(
            source=UnexpectedSource(),
            now=lambda: NOW,
        ).find(category="all", limit=8, source_mode="archive")

        self.assertEqual("all", result.category)
        self.assertEqual("archive", result.mode)
        self.assertGreaterEqual(
            len({candidate.category for candidate in result.candidates}),
            3,
        )
        self.assertEqual(
            sorted(
                (candidate.score for candidate in result.candidates),
                reverse=True,
            ),
            [candidate.score for candidate in result.candidates],
        )

    def test_all_mixed_mode_preserves_global_source_ratio(self) -> None:
        result = AutoTopicFinder(
            source=CategorySource(),
            now=lambda: NOW,
        ).find(category="all", limit=10, source_mode="mixed")

        self.assertEqual("mixed", result.mode)
        self.assertEqual(4, sum(item.source_count > 0 for item in result.candidates))
        self.assertEqual(6, sum(item.source_count == 0 for item in result.candidates))

    def test_game_patch_is_rejected_by_brand_filter(self) -> None:
        items = [
            TopicSourceItem(
                title="문명7 대격변 패치 업데이트 공개",
                url="https://example.com/game",
                source="게임뉴스",
                published_at="2026-07-17T10:00:00+00:00",
            )
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="history", limit=1)

        self.assertNotIn("문명7", result.candidates[0].topic)
        self.assertEqual(0, result.candidates[0].source_count)

    def test_medical_press_release_is_rejected_by_brand_filter(self) -> None:
        items = [
            TopicSourceItem(
                title="코로나19 후유증 브레인 포그 치료제 연구 결과 발표",
                url="https://example.com/medical",
                source="의학뉴스",
                published_at="2026-07-17T10:00:00+00:00",
            )
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="science", limit=1)

        self.assertNotIn("코로나19", result.candidates[0].topic)
        self.assertEqual(0, result.candidates[0].source_count)

    def test_generic_science_quote_without_hook_is_rejected(self) -> None:
        items = [
            TopicSourceItem(
                title="노벨물리학상 교수 과학 연구는 평생을 바칠 가치",
                url="https://example.com/interview",
                source="과학뉴스",
                published_at="2026-07-17T10:00:00+00:00",
            )
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="science", limit=1)

        self.assertNotIn("평생을 바칠 가치", result.candidates[0].topic)
        self.assertEqual(0, result.candidates[0].source_count)


if __name__ == "__main__":
    unittest.main()
