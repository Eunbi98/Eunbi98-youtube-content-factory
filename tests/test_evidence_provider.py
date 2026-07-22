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
    def collect(
        self,
        _: dict,
        *,
        search_queries: list[str] | None = None,
    ) -> list[dict[str, str]]:
        if not search_queries:
            raise AssertionError("English search queries were not provided")
        return _source_documents()


def _model_response(payload: dict, evidence_payload: dict) -> dict:
    name = payload["response_format"]["json_schema"]["name"]
    content = (
        {
            "englishTopic": "Martian polygonal ridges",
            "queries": [
                "Mars polygonal ridges geology",
                "Curiosity polygon fractures research",
            ],
        }
        if name == "factory_research_queries"
        else evidence_payload
    )
    return {"choices": [{"message": {"content": json.dumps(content)}}]}


class EvidenceProviderTests(unittest.TestCase):
    def test_provider_uses_public_sources_and_structured_output(self) -> None:
        captured: list[dict] = []
        result_payload = _provider_result()

        def transport(payload: dict) -> dict:
            captured.append(payload)
            return _model_response(payload, result_payload)

        result = GithubModelsEvidenceProvider(
            client=GithubModelsClient(
                token="test-token",
                transport=transport,
            ),
            source_collector=_SourceCollector(),
        ).collect(_job())

        self.assertEqual(2, len(captured))
        evidence_request = captured[1]
        self.assertTrue(
            evidence_request["response_format"]["json_schema"]["strict"]
        )
        self.assertEqual("openai/gpt-4.1", evidence_request["model"])
        self.assertNotIn("tools", evidence_request)
        self.assertEqual("complete", result["status"])
        self.assertEqual(3, len(result["citations"]))

    def test_provider_retries_when_model_selects_duplicate_domains(self) -> None:
        captured: list[dict] = []
        insufficient = _provider_result()
        insufficient["items"][1]["source_url"] = "https://science.nasa.gov/second"
        insufficient["items"][2]["source_url"] = "https://science.nasa.gov/third"
        complete = _provider_result()
        source_documents = _source_documents()
        source_documents.extend(
            {
                "id": f"retry_source_{index}",
                "title": item["title"],
                "source_name": item["source_name"],
                "source_url": item["source_url"],
                "source_tier": item["source_tier"],
                "published_at": item["published_at"],
                "text": item["claim"],
            }
            for index, item in enumerate(insufficient["items"][1:], start=1)
        )

        class RetrySourceCollector:
            def collect(
                self,
                _: dict,
                *,
                search_queries: list[str] | None = None,
            ) -> list[dict[str, str]]:
                if not search_queries:
                    raise AssertionError("English search queries were not provided")
                return source_documents

        def transport(payload: dict) -> dict:
            captured.append(payload)
            name = payload["response_format"]["json_schema"]["name"]
            if name == "factory_research_queries":
                return _model_response(payload, complete)
            evidence_calls = sum(
                item["response_format"]["json_schema"]["name"]
                == "factory_evidence_result"
                for item in captured
            )
            selected = insufficient if evidence_calls == 1 else complete
            return _model_response(payload, selected)

        result = GithubModelsEvidenceProvider(
            client=GithubModelsClient(token="test-token", transport=transport),
            source_collector=RetrySourceCollector(),
        ).collect(_job())

        self.assertEqual("complete", result["status"])
        self.assertEqual(3, len(captured))
        self.assertIn(
            "Retry once",
            captured[2]["messages"][0]["content"],
        )

    def test_environment_key_is_required(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(GithubModelsError):
                GithubModelsClient.from_environment()

    def test_provider_rejects_invented_source_url(self) -> None:
        payload = _provider_result()
        payload["items"][0]["source_url"] = "https://invented.example/fake"

        def transport(request: dict) -> dict:
            return _model_response(request, payload)

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

        evidence = EvidenceService().build_evidence(
            topic="화성의 벌집 모양 구조물",
            provider_result=provider_result,
        )

        self.assertEqual("verified", evidence["status"])

    def test_evidence_gate_rejects_missing_counterpoint_and_uncertainty(self) -> None:
        provider_result = _provider_result()
        provider_result["items"][1]["evidence_type"] = "fact"
        provider_result["uncertainties"] = []

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
