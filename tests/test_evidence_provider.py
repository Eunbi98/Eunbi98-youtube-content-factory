from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.research.evidence_service import (  # noqa: E402
    EvidenceGateError,
    EvidenceService,
)
from projects.ai.github_models_client import (  # noqa: E402
    GithubModelsClient,
    GithubModelsError,
)
from projects.research.github_models_evidence_provider import (  # noqa: E402
    EvidenceProviderError,
    GithubModelsEvidenceProvider,
)


def _job() -> dict:
    return {
        "version": "1.0",
        "jobId": "ep015-test",
        "episodeId": "ep015",
        "category": "space",
        "status": "research_planned",
        "selectedTopic": {
            "topic": "화성의 벌집 모양 구조물",
            "angle": "이 구조물은 어떻게 만들어졌을까?",
        },
        "researchPlan": {
            "questions": ["무엇이 발견됐는가?"],
            "queries": ["NASA Mars honeycomb polygons"],
            "sourceSeeds": [],
        },
        "artifacts": {"evidence": None},
        "nextAction": "collect_evidence",
    }


def _provider_result() -> dict:
    return {
        "status": "complete",
        "summary": "화성 표면의 다각형 융기 구조를 조사했다.",
        "uncertainties": ["정확한 형성 과정은 추가 분석이 필요하다."],
        "items": [
            {
                "title": "In the Land of the Polygons",
                "claim": (
                    "NASA 큐리오시티 팀은 궤도에서 밝고 매끈해 보인 지형에 "
                    "도착한 뒤 벌집처럼 이어진 다각형 구조를 확인했다."
                ),
                "source_name": "NASA Science",
                "source_url": "https://science.nasa.gov/example-polygons",
                "source_tier": "official",
                "evidence_type": "fact",
                "published_at": "2026-07-01",
                "keywords": ["Mars", "Curiosity", "polygons", "사진"],
            },
            {
                "title": "Polygonal fractures on Mars",
                "claim": (
                    "화성의 다각형 균열은 건조, 퇴적물 변화, 지하 얼음 등 "
                    "여러 지질 과정으로 만들어질 수 있다."
                ),
                "source_name": "Planetary Science Journal",
                "source_url": "https://example.edu/mars-polygons",
                "source_tier": "academic",
                "evidence_type": "counterpoint",
                "published_at": "2025-05-01",
                "keywords": ["geology", "fracture", "Mars"],
            },
            {
                "title": "Curiosity sees a Martian honeycomb",
                "claim": (
                    "보도 사진에는 비슷한 크기의 다각형 융기와 주변의 어두운 "
                    "암석 조각들이 함께 나타난다."
                ),
                "source_name": "Space News",
                "source_url": "https://example.com/mars-honeycomb",
                "source_tier": "news",
                "evidence_type": "case",
                "published_at": "2026-07-14",
                "keywords": ["Mars", "image", "rocks"],
            },
        ],
        "citations": [
            {
                "title": "NASA Science",
                "url": "https://science.nasa.gov/example-polygons",
            }
        ],
        "provider": "github_models_public_sources",
        "model": "openai/gpt-4.1",
    }


def _source_documents() -> list[dict[str, str]]:
    return [
        {
            "id": "source_1",
            "title": item["title"],
            "source_name": item["source_name"],
            "source_url": item["source_url"],
            "source_tier": item["source_tier"],
            "published_at": item["published_at"],
            "text": item["claim"],
        }
        for item in _provider_result()["items"]
    ]


class _SourceCollector:
    def collect(self, _: dict) -> list[dict[str, str]]:
        return _source_documents()


class EvidenceProviderTests(unittest.TestCase):
    def test_provider_uses_public_sources_and_structured_output(self) -> None:
        captured: dict = {}
        result_payload = _provider_result()

        def transport(payload: dict) -> dict:
            captured.update(payload)
            return {
                "choices": [
                    {"message": {"content": json.dumps(result_payload)}}
                ]
            }

        result = GithubModelsEvidenceProvider(
            client=GithubModelsClient(
                token="test-token",
                transport=transport,
            ),
            source_collector=_SourceCollector(),
        ).collect(_job())

        self.assertTrue(captured["response_format"]["json_schema"]["strict"])
        self.assertEqual("openai/gpt-4.1", captured["model"])
        self.assertNotIn("tools", captured)
        self.assertEqual("complete", result["status"])
        self.assertEqual(3, len(result["citations"]))

    def test_environment_key_is_required(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GithubModelsError):
                GithubModelsClient.from_environment()

    def test_provider_rejects_invented_source_url(self) -> None:
        payload = _provider_result()
        payload["items"][0]["source_url"] = "https://invented.example/fake"

        def transport(_: dict) -> dict:
            return {
                "choices": [
                    {"message": {"content": json.dumps(payload)}}
                ]
            }

        with self.assertRaises(EvidenceProviderError):
            GithubModelsEvidenceProvider(
                client=GithubModelsClient(
                    token="test-token",
                    transport=transport,
                ),
                source_collector=_SourceCollector(),
            ).collect(_job())

    def test_evidence_gate_scores_valid_sources(self) -> None:
        evidence = EvidenceService().build_evidence(
            topic="화성의 벌집 모양 구조물",
            provider_result=_provider_result(),
        )

        self.assertEqual("verified", evidence["status"])
        self.assertEqual(3, len(evidence["items"]))
        self.assertTrue(
            all("total_score" in item for item in evidence["items"])
        )

    def test_evidence_gate_rejects_missing_counterpoint(self) -> None:
        provider_result = _provider_result()
        provider_result["items"][1]["evidence_type"] = "fact"

        with self.assertRaises(EvidenceGateError):
            EvidenceService().build_evidence(
                topic="화성의 벌집 모양 구조물",
                provider_result=provider_result,
            )

    def test_job_advances_only_after_evidence(self) -> None:
        updated = EvidenceService.advance_job(
            _job(),
            evidence_path="projects/episodes/ep015/evidence.json",
        )

        self.assertEqual("evidence_ready", updated["status"])
        self.assertEqual("build_episode_spec", updated["nextAction"])
        self.assertEqual(
            "projects/episodes/ep015/evidence.json",
            updated["artifacts"]["evidence"],
        )


if __name__ == "__main__":
    unittest.main()
