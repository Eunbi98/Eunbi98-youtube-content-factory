from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from projects.production.episode_quality import (  # noqa: E402
    EpisodeQualityError,
    EpisodeQualityService,
    TimelineQualityService,
)


def _job() -> dict:
    return {
        "episodeId": "ep015",
        "status": "evidence_ready",
        "artifacts": {},
        "selectedTopic": {
            "topic": "국내 연구진, 화성에서 검은 돌 발견",
            "sources": [
                {"title": "국내 연구진, 화성에서 검은 돌 발견 - 뉴스"}
            ],
        },
    }


def _evidence() -> dict:
    return {
        "status": "verified",
        "items": [
            {"id": "evidence_1", "source_url": "https://source-a.example/a"},
            {"id": "evidence_2", "source_url": "https://source-b.example/b"},
            {"id": "evidence_3", "source_url": "https://source-c.example/c"},
        ],
    }


def _spec() -> dict:
    scenes = []
    for index, scene_type in enumerate(
        ["hook", "answer", "story", "fact", "ending"],
        start=1,
    ):
        narration = f"검증된 장면 {index}의 설명입니다."
        if scene_type == "ending":
            narration = "여러분은 어떤 설명이 맞다고 생각하시나요?"
        scenes.append(
            {
                "type": scene_type,
                "title": f"장면 {index}",
                "narration": narration,
                "keywords": ["Mars Curiosity", "Gale Crater"],
                "evidenceIds": ["evidence_1"],
            }
        )
    return {
        "episodeId": "ep015",
        "title": "테스트",
        "scenes": scenes,
    }


def _metadata() -> dict:
    return {
        "title": "화성의 검은 돌은 어디에서 왔을까?",
        "description": (
            "화성에서 발견된 검은 돌을 알고 계셨나요?\n\n"
            "탐사 로버가 낯선 암석을 촬영했습니다.\n\n"
            "아직 그 기원은 정확히 밝혀지지 않았는데요.\n\n"
            "여러분은 이 돌이 어디에서 왔다고 생각하시나요?\n\n"
            "댓글로 여러분의 생각을 남겨주세요!"
        ),
        "pinnedComment": (
            "화성의 검은 돌은 어디에서 왔다고 생각하시나요?\n\n"
            "댓글로 여러분의 추리를 알려주세요!"
        ),
        "tags": ["1", "2", "3", "쇼츠", "shorts"],
        "sources": [
            "https://source-a.example/a",
            "https://source-b.example/b",
            "https://source-c.example/c",
        ],
    }


class EpisodeQualityTests(unittest.TestCase):
    def _write_spec(self, directory: Path, payload: dict) -> Path:
        path = directory / "episode.json"
        path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return path

    def test_verified_episode_advances_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            spec_path = self._write_spec(directory, _spec())
            metadata_path = directory / "metadata.json"
            updated = EpisodeQualityService().validate_and_advance(
                job_payload=_job(),
                evidence_payload=_evidence(),
                episode_spec_path=spec_path,
                metadata_payload=_metadata(),
                metadata_path=metadata_path,
            )

        self.assertEqual("episode_ready", updated["status"])
        self.assertEqual("build_timeline", updated["nextAction"])

    def test_unknown_evidence_id_is_rejected(self) -> None:
        payload = _spec()
        payload["scenes"][2]["evidenceIds"] = ["unknown"]
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            spec_path = self._write_spec(directory, payload)
            with self.assertRaises(EpisodeQualityError):
                EpisodeQualityService().validate_and_advance(
                    job_payload=_job(),
                    evidence_payload=_evidence(),
                    episode_spec_path=spec_path,
                    metadata_payload=_metadata(),
                    metadata_path=directory / "metadata.json",
                )

    def test_ending_without_question_is_rejected(self) -> None:
        payload = _spec()
        payload["scenes"][-1]["narration"] = "조사는 계속됩니다."
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            spec_path = self._write_spec(directory, payload)
            with self.assertRaises(EpisodeQualityError):
                EpisodeQualityService().validate_and_advance(
                    job_payload=_job(),
                    evidence_payload=_evidence(),
                    episode_spec_path=spec_path,
                    metadata_payload=_metadata(),
                    metadata_path=directory / "metadata.json",
                )

    def test_unverified_metadata_source_is_rejected(self) -> None:
        metadata = _metadata()
        metadata["sources"][2] = "https://invented.example/source"
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            spec_path = self._write_spec(directory, _spec())
            with self.assertRaises(EpisodeQualityError):
                EpisodeQualityService().validate_and_advance(
                    job_payload=_job(),
                    evidence_payload=_evidence(),
                    episode_spec_path=spec_path,
                    metadata_payload=metadata,
                    metadata_path=directory / "metadata.json",
                )

    def test_copied_news_title_is_rejected(self) -> None:
        metadata = _metadata()
        metadata["title"] = "국내 연구진, 화성에서 검은 돌 발견"
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            spec_path = self._write_spec(directory, _spec())
            with self.assertRaisesRegex(
                EpisodeQualityError,
                "기사 또는 선택 주제 제목과 너무 유사",
            ):
                EpisodeQualityService().validate_and_advance(
                    job_payload=_job(),
                    evidence_payload=_evidence(),
                    episode_spec_path=spec_path,
                    metadata_payload=metadata,
                    metadata_path=directory / "metadata.json",
                )

    def test_title_with_hashtag_is_rejected(self) -> None:
        metadata = _metadata()
        metadata["title"] += " #쇼츠 #shorts"
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            spec_path = self._write_spec(directory, _spec())
            with self.assertRaisesRegex(EpisodeQualityError, "해시태그"):
                EpisodeQualityService().validate_and_advance(
                    job_payload=_job(),
                    evidence_payload=_evidence(),
                    episode_spec_path=spec_path,
                    metadata_payload=metadata,
                    metadata_path=directory / "metadata.json",
                )

    def test_description_without_channel_style_is_rejected(self) -> None:
        metadata = _metadata()
        metadata["description"] = "기사 내용을 한 문단으로 요약했습니다."
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            spec_path = self._write_spec(directory, _spec())
            with self.assertRaisesRegex(
                EpisodeQualityError,
                "문단이 최소 4개",
            ):
                EpisodeQualityService().validate_and_advance(
                    job_payload=_job(),
                    evidence_payload=_evidence(),
                    episode_spec_path=spec_path,
                    metadata_payload=metadata,
                    metadata_path=directory / "metadata.json",
                )

    def test_timeline_and_queries_advance_media_plan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            timeline_path = directory / "timeline.json"
            timeline_path.write_text(
                json.dumps(
                    {
                        "episodeId": "EP015",
                        "scenes": [
                            {"narration": "같은 원문", "caption": "같은 원문"}
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            queries_path = directory / "media_queries.json"
            queries_path.write_text(
                json.dumps(
                    {"scenes": [{"primaryQuery": "Mars terrain"}]},
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            job = _job()
            job["status"] = "episode_ready"
            updated = TimelineQualityService().validate_and_advance(
                job_payload=job,
                timeline_path=timeline_path,
                media_queries_path=queries_path,
            )

        self.assertEqual("media_planned", updated["status"])
        self.assertEqual("collect_media", updated["nextAction"])

    def test_timeline_caption_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            directory = Path(temp_dir)
            timeline_path = directory / "timeline.json"
            timeline_path.write_text(
                json.dumps(
                    {
                        "episodeId": "EP015",
                        "scenes": [{"narration": "원문", "caption": "다른 자막"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            queries_path = directory / "media_queries.json"
            queries_path.write_text(
                json.dumps({"scenes": [{"primaryQuery": "Mars"}]}),
                encoding="utf-8",
            )
            job = _job()
            job["status"] = "episode_ready"
            with self.assertRaises(EpisodeQualityError):
                TimelineQualityService().validate_and_advance(
                    job_payload=job,
                    timeline_path=timeline_path,
                    media_queries_path=queries_path,
                )


if __name__ == "__main__":
    unittest.main()
