from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.ai.github_models_client import GithubModelsClient  # noqa: E402
from projects.production.github_models_episode_provider import (  # noqa: E402
    EpisodeProviderError,
    GithubModelsEpisodeProvider,
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
            "title": "우주에서는 왜 아무 소리도 들리지 않을까? #쇼츠 #shorts",
            "description": (
                "우주가 왜 그렇게 조용한지 알고 계셨나요?\n\n"
                "우주는 진공에 가까워 소리가 멀리 전달되지 않습니다.\n\n"
                "영화 속 우주 폭발음도 실제로는 들리지 않는데요.\n\n"
                "여러분이라면 아무 소리도 없는 우주에서 버틸 수 있을까요?\n\n"
                "댓글로 여러분의 생각을 남겨주세요!"
            ),
            "tags": ["우주", "과학", "미스터리", "쇼츠", "NASA"],
            "pinnedComment": (
                "우주가 완전히 조용하다는 사실을 알고 계셨나요?\n\n"
                "댓글로 여러분의 생각을 알려주세요!"
            ),
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
                "choices": [
                    {"message": {"content": json.dumps(_package())}}
                ]
            }

        result = GithubModelsEpisodeProvider(
            client=GithubModelsClient(
                token="test-token",
                transport=transport,
            )
        ).build(job_payload=_job(), evidence_payload=_evidence())

        schema = captured["response_format"]["json_schema"]
        self.assertTrue(schema["strict"])
        self.assertEqual(
            6,
            schema["schema"]["properties"]["episode"]["properties"]["scenes"]["minItems"],
        )
        self.assertEqual("ep016", result["episode"]["episodeId"])
        self.assertNotIn("#", result["metadata"]["title"])
        self.assertIn("쇼츠", result["metadata"]["tags"])
        self.assertIn("shorts", result["metadata"]["tags"])
        self.assertIn(
            "not copied or lightly edited",
            captured["messages"][0]["content"],
        )

    def test_provider_rejects_wrong_episode_identity(self) -> None:
        package = _package()
        package["episode"]["episodeId"] = "ep999"

        def transport(_: dict) -> dict:
            return {
                "choices": [
                    {"message": {"content": json.dumps(package)}}
                ]
            }

        with self.assertRaises(EpisodeProviderError):
            GithubModelsEpisodeProvider(
                client=GithubModelsClient(
                    token="test-token",
                    transport=transport,
                )
            ).build(job_payload=_job(), evidence_payload=_evidence())

    def test_provider_normalizes_render_colors(self) -> None:
        package = _package()
        package["episode"]["theme"]["titleColor"] = "#2980b9"
        package["episode"]["theme"]["captionColor"] = "#222222"

        def transport(_: dict) -> dict:
            return {
                "choices": [
                    {"message": {"content": json.dumps(package)}}
                ]
            }

        result = GithubModelsEpisodeProvider(
            client=GithubModelsClient(
                token="test-token",
                transport=transport,
            )
        ).build(job_payload=_job(), evidence_payload=_evidence())

        self.assertEqual("#7BFEB4", result["episode"]["theme"]["titleColor"])
        self.assertEqual("#FFFFFF", result["episode"]["theme"]["captionColor"])

    def test_provider_requires_verified_evidence(self) -> None:
        evidence = _evidence()
        evidence["status"] = "draft"
        with self.assertRaises(EpisodeProviderError):
            GithubModelsEpisodeProvider(
                client=GithubModelsClient(token="test-token")
            ).build(
                job_payload=_job(),
                evidence_payload=evidence,
            )


if __name__ == "__main__":
    unittest.main()
