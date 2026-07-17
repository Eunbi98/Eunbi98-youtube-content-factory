from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.production.production_job import (  # noqa: E402
    ProductionJobError,
    ProductionJobPlanner,
)
from projects.production.select_topic import next_episode_id  # noqa: E402


NOW = datetime(2026, 7, 17, 15, 30, tzinfo=timezone.utc)


def _candidate_payload() -> dict:
    return {
        "category": "mystery",
        "candidates": [
            {
                "rank": 1,
                "category": "mystery",
                "topic": "화성에서 발견된 미스터리 구조물",
                "angle": "이 구조물은 어떻게 만들어졌을까?",
                "score": 79.0,
                "reasons": ["최근 7일 이내 보도"],
                "search_queries": ["Mars mystery structure NASA"],
                "source_count": 1,
                "sources": [
                    {
                        "title": "화성 미스터리 구조물",
                        "url": "https://example.com/mars",
                        "source": "과학뉴스",
                    }
                ],
            },
            {
                "rank": 2,
                "category": "mystery",
                "topic": "비잔틴 도시 유적",
                "angle": "도시는 왜 사라졌을까?",
                "score": 73.0,
                "reasons": [],
                "search_queries": [],
                "source_count": 2,
                "sources": [],
            },
        ],
    }


class ProductionJobTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = ProductionJobPlanner(now=lambda: NOW)

    def test_selected_candidate_becomes_research_job(self) -> None:
        payload = _candidate_payload()
        candidate = self.planner.select_candidate(payload, rank=1)
        job = self.planner.create(
            episode_id="ep015",
            category=payload["category"],
            candidate=candidate,
        )
        result = job.to_dict()

        self.assertEqual("ep015", result["episodeId"])
        self.assertEqual("research_planned", result["status"])
        self.assertEqual("collect_evidence", result["nextAction"])
        self.assertEqual(
            "화성에서 발견된 미스터리 구조물",
            result["selectedTopic"]["topic"],
        )
        self.assertGreaterEqual(
            len(result["researchPlan"]["queries"]),
            5,
        )
        self.assertEqual(
            3,
            result["researchPlan"]["sourcePolicy"]["minimumSources"],
        )

    def test_rank_selects_requested_candidate(self) -> None:
        candidate = self.planner.select_candidate(
            _candidate_payload(),
            rank=2,
        )
        self.assertEqual("비잔틴 도시 유적", candidate["topic"])

    def test_missing_rank_is_rejected(self) -> None:
        with self.assertRaises(ProductionJobError):
            self.planner.select_candidate(_candidate_payload(), rank=10)

    def test_invalid_episode_id_is_rejected(self) -> None:
        candidate = self.planner.select_candidate(
            _candidate_payload(),
            rank=1,
        )
        with self.assertRaises(ProductionJobError):
            self.planner.create(
                episode_id="15",
                category="mystery",
                candidate=candidate,
            )

    def test_next_episode_id_uses_highest_existing_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root_dir = Path(temp_dir)
            episodes_dir = root_dir / "projects" / "episodes"
            (episodes_dir / "ep009").mkdir(parents=True)
            (episodes_dir / "ep014").mkdir()
            (episodes_dir / "notes").mkdir()

            result = next_episode_id(root_dir)

        self.assertEqual("ep015", result)


if __name__ == "__main__":
    unittest.main()
