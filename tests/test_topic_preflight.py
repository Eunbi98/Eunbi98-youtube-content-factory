from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

MEDIA_DIR = ROOT_DIR / "projects" / "media"
if str(MEDIA_DIR) not in sys.path:
    sys.path.insert(0, str(MEDIA_DIR))

from provider_models import MediaCandidate  # noqa: E402
from projects.research.public_source_collector import PublicSourceError  # noqa: E402
from projects.topic.topic_preflight import CandidatePreflightService  # noqa: E402


def _candidate(topic: str = "화성에서 발견된 벌집 모양 지형") -> dict:
    return {
        "rank": 1,
        "category": "space",
        "topic": topic,
        "angle": "이 지형은 어떻게 만들어졌을까?",
        "score": 82.0,
        "reasons": ["영상 자료로 표현하기 쉬운 주제"],
        "search_queries": ["Mars honeycomb terrain"],
        "production_ready": True,
        "readiness_score": 100,
        "readiness_checks": ["기본 주제 검사 통과"],
    }


def _source_documents() -> list[dict[str, str]]:
    return [
            {
                "id": "source_1",
                "title": "NASA Mars polygons",
                "source_name": "NASA Science",
                "source_url": "https://science.nasa.gov/mars-polygons",
                "source_tier": "official",
                "published_at": "2026-07-01",
                "text": "NASA 관측 사진에는 화성 표면의 다각형 융기 구조가 선명하게 나타난다.",
            },
            {
                "id": "source_2",
                "title": "Polygonal terrain study",
                "source_name": "Planetary Science Journal",
                "source_url": "https://example.edu/polygonal-terrain",
                "source_tier": "academic",
                "published_at": "2025-05-01",
                "text": "연구진은 건조와 지하 얼음 등 여러 과정이 다각형 지형을 만들 수 있다고 설명한다.",
            },
    ]


class FakeSourceCollector:
    def collect(
        self,
        job_payload: dict,
        *,
        search_queries: list[str] | None = None,
    ) -> list[dict[str, str]]:
        return _source_documents()


class FailingSourceCollector:
    def collect(
        self,
        job_payload: dict,
        *,
        search_queries: list[str] | None = None,
    ) -> list[dict[str, str]]:
        raise PublicSourceError("독립 출처를 확보하지 못했습니다.")


class FakeMediaProvider:
    def __init__(self, provider: str, count: int) -> None:
        self.provider = provider
        self.count = count

    def search(self, *, query: str, limit: int) -> list[MediaCandidate]:
        return [
            MediaCandidate(
                provider=self.provider,
                media_id=f"{query}-{index}",
                title=f"{query} image {index}",
                query=query,
                media_type="image",
                mime_type="image/jpeg",
                source_url=f"https://media.example/{self.provider}/{index}",
                download_url=f"https://media.example/{self.provider}/{index}.jpg",
                thumbnail_url=None,
                author="Test",
                author_url=None,
                license_name="CC BY 4.0",
                license_url="https://creativecommons.org/licenses/by/4.0/",
                width=1600,
                height=1200,
                orientation="landscape",
                file_extension=".jpg",
            )
            for index in range(self.count)
        ]


class TopicPreflightTests(unittest.TestCase):
    def _service(
        self,
        *,
        source_collector: object | None = None,
        media_count: int = 3,
    ) -> CandidatePreflightService:
        return CandidatePreflightService(
            source_collector=source_collector or FakeSourceCollector(),
            media_providers={
                "openverse": FakeMediaProvider("openverse", media_count),
            },
            minimum_media_candidates=5,
            minimum_media_queries=2,
        )

    def test_keeps_only_candidate_with_reusable_evidence_and_media(self) -> None:
        result = self._service().filter_payload(
            {"category": "space", "mode": "live", "candidates": [_candidate()]},
            limit=5,
        )

        self.assertEqual(1, result["candidate_count"])
        accepted = result["candidates"][0]
        self.assertEqual("verified", accepted["source_preflight"]["status"])
        self.assertEqual(2, len(accepted["preflight_sources"]))
        self.assertGreaterEqual(
            accepted["preflight_media"]["candidateCount"],
            5,
        )
        self.assertEqual(2, accepted["evidence_preflight"]["domain_count"])
        self.assertTrue(accepted["production_ready"])

    def test_research_failure_removes_candidate_from_result(self) -> None:
        result = self._service(
            source_collector=FailingSourceCollector(),
        ).filter_payload(
            {"category": "space", "mode": "live", "candidates": [_candidate()]},
            limit=5,
        )

        self.assertEqual(0, result["candidate_count"])
        self.assertEqual(1, len(result["preflight"]["rejected"]))

    def test_distinct_doi_works_count_as_independent_sources(self) -> None:
        sources = _source_documents()
        for index, source in enumerate(sources, start=1):
            source["source_tier"] = "academic"
            source["source_url"] = f"https://doi.org/10.1000/work-{index}"

        class DoiCollector:
            def collect(
                self,
                *args: object,
                **kwargs: object,
            ) -> list[dict[str, str]]:
                return sources

        result = self._service(source_collector=DoiCollector()).filter_payload(
            {"category": "space", "mode": "archive", "candidates": [_candidate()]},
            limit=1,
        )

        self.assertEqual(1, result["candidate_count"])
        self.assertEqual(
            2,
            result["candidates"][0]["source_preflight"]["domainCount"],
        )

    def test_insufficient_media_removes_candidate_from_result(self) -> None:
        result = self._service(media_count=1).filter_payload(
            {"category": "space", "mode": "live", "candidates": [_candidate()]},
            limit=5,
        )

        self.assertEqual(0, result["candidate_count"])
        self.assertIn("이미지", result["preflight"]["rejected"][0]["reason"])

    def test_result_stops_at_requested_limit(self) -> None:
        candidates = [_candidate(f"화성 다각형 지형 {index}") for index in range(4)]
        result = self._service().filter_payload(
            {"category": "space", "mode": "live", "candidates": candidates},
            limit=2,
        )

        self.assertEqual(2, result["candidate_count"])
        self.assertEqual([1, 2], [item["rank"] for item in result["candidates"]])

    def test_preflight_caps_expensive_candidate_checks(self) -> None:
        candidates = [_candidate(f"화성 다각형 지형 {index}") for index in range(12)]
        service = CandidatePreflightService(
            source_collector=FailingSourceCollector(),
            media_providers={"openverse": FakeMediaProvider("openverse", 3)},
            maximum_candidates_checked=3,
        )

        result = service.filter_payload(
            {"category": "space", "mode": "live", "candidates": candidates},
            limit=5,
        )

        self.assertEqual(3, result["preflight"]["checked"])
        self.assertEqual(3, len(result["preflight"]["rejected"]))


if __name__ == "__main__":
    unittest.main()
