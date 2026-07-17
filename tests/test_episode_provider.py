from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.production.openai_episode_provider import (  # noqa: E402
    EpisodeProviderError,
    OpenAIEpisodeProvider,
)


def _job() -> dict:
    return {
        "episodeId": "ep016",
        "category": "space",
        "status": "evidence_ready",
        "selectedTopic": {"topic": "우주의 소리", "angle": "왜 조용할까?"},
    }


def _evidence() -> dict:
    return {
        "status": "verified",
        "summary": "검증된 요약",
        "uncertainties": ["직접 들을 수 있는 소리는 아니다."],
        "items": [
            {
                "id": "evidence_1",
                "claim": "우주는 진공에 가깝다.",
                "source_url": "https://science.nasa.gov/example",
            }
        ],
    }


def _package() -> dict:
    scenes = []
    for index, scene_type in enumerate(
        ["hook", "answer", "story", "fact", "fact", "ending"],
        start=1,
    ):
        narration = f"검증된 설명 {index}입니다."
        if scene_type == "ending":
            narration = "여러분은 우주의 침묵을 어떻게 생각하시나요?"
        scenes.append(
            {
                "type": scene_type,
                "title": f"장면 {index}",
                "narration": narration,
                "keywords": ["NASA space", "vacuum universe"],
                "evidenceIds": ["evidence_1"],
            }
        )
    return {
        "episode": {
            "version": "1.0",
            "episodeId": "ep016",
            "channel": "space",
            "mediaSource": "automatic",
            "title": "우주는 왜 조용할까",
            "theme": {
                "backgroundColor": "#080B10",
                "titleColor": "#FFB36B",
                "captionColor": "#FFFFFF",
                "accentColor": "#FF6B35",
            },
            "scenes": scenes,
        },
        "metadata": {
            "episodeId": "ep016",
            "title": "우주는 왜 조용할까?",
            "description": "검증된 설명",
            "tags": ["우주", "과학", "미스터리", "쇼츠", "NASA"],
            "pinnedComment": "여러분은 어떻게 생각하시나요?",
            "sources": [
                "https://science.nasa.gov/example",
                "https://example.edu/paper",
                "https://example.com/reference",
            ],
        },
    }


class EpisodeProviderTests(unittest.TestCase):
    def test_provider_uses_strict_structured_output(self) -> None:
        captured: dict = {}

        def transport(payload: dict) -> dict:
            captured.update(payload)
            return {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "output_text",
                                "text": json.dumps(_package()),
                            }
                        ],
                    }
                ],
            }

        result = OpenAIEpisodeProvider(
            api_key="test-key",
            transport=transport,
        ).build(job_payload=_job(), evidence_payload=_evidence())

        self.assertTrue(captured["text"]["format"]["strict"])
        self.assertEqual(6, captured["text"]["format"]["schema"]["properties"]["episode"]["properties"]["scenes"]["minItems"])
        self.assertFalse(captured["store"])
        self.assertEqual("ep016", result["episode"]["episodeId"])

    def test_provider_rejects_wrong_episode_identity(self) -> None:
        package = _package()
        package["episode"]["episodeId"] = "ep999"

        def transport(_: dict) -> dict:
            return {
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps(package)}
                        ],
                    }
                ],
            }

        with self.assertRaises(EpisodeProviderError):
            OpenAIEpisodeProvider(
                api_key="test-key",
                transport=transport,
            ).build(job_payload=_job(), evidence_payload=_evidence())

    def test_provider_requires_verified_evidence(self) -> None:
        evidence = _evidence()
        evidence["status"] = "draft"
        with self.assertRaises(EpisodeProviderError):
            OpenAIEpisodeProvider(api_key="test-key").build(
                job_payload=_job(),
                evidence_payload=evidence,
            )


if __name__ == "__main__":
    unittest.main()
