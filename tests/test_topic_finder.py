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
                title="오래된 기록을 다시 읽는 방법 - 뉴스C",
                url="https://example.com/c",
                source="뉴스C",
                published_at="2026-07-03T08:00:00+00:00",
            ),
        ]
        result = AutoTopicFinder(
            source=FakeSource(items),
            now=lambda: NOW,
        ).find(category="mystery", limit=2)

        self.assertEqual("live", result.mode)
        self.assertIn("고대 유적", result.candidates[0].topic)
        self.assertEqual(2, result.candidates[0].source_count)
        self.assertGreater(
            result.candidates[0].score,
            result.candidates[1].score,
        )

    def test_source_failure_returns_ten_safe_candidates(self) -> None:
        result = AutoTopicFinder(
            source=FailingSource(),
            now=lambda: NOW,
        ).find(category="science", limit=10)

        self.assertEqual("fallback", result.mode)
        self.assertEqual(10, result.candidate_count)
        self.assertEqual(1, result.candidates[0].rank)
        self.assertEqual(10, result.candidates[-1].rank)
        self.assertTrue(result.warnings)

    def test_partial_live_results_are_filled_from_catalog(self) -> None:
        items = [
            TopicSourceItem(
                title="화성에서 새로운 물의 흔적 발견 - 우주뉴스",
                url="https://example.com/mars",
                source="우주뉴스",
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

    def test_result_is_json_serializable_shape(self) -> None:
        result = AutoTopicFinder(
            source=FailingSource(),
            now=lambda: NOW,
        ).find(category="history", limit=1)
        payload = result.to_dict()

        self.assertEqual("history", payload["category"])
        self.assertEqual(1, payload["candidate_count"])
        self.assertEqual(1, payload["candidates"][0]["rank"])


if __name__ == "__main__":
    unittest.main()
