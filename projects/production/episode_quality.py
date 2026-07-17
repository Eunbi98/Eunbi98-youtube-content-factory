from __future__ import annotations

import copy
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DIRECTOR_DIR = Path(__file__).resolve().parents[1] / "director"
if str(DIRECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(DIRECTOR_DIR))

from episode_spec import EpisodeSpecError, load_episode_spec  # noqa: E402


class EpisodeQualityError(ValueError):
    """검증된 근거와 제작 명세가 품질 기준을 통과하지 못함."""


class EpisodeQualityService:
    def validate_and_advance(
        self,
        *,
        job_payload: dict[str, Any],
        evidence_payload: dict[str, Any],
        episode_spec_path: Path,
        metadata_payload: dict[str, Any],
        metadata_path: Path,
    ) -> dict[str, Any]:
        if job_payload.get("status") != "evidence_ready":
            raise EpisodeQualityError(
                "evidence_ready 상태의 작업만 Episode 품질 검사를 할 수 있습니다."
            )
        if evidence_payload.get("status") != "verified":
            raise EpisodeQualityError("검증 완료된 Evidence가 필요합니다.")

        expected_episode_id = str(job_payload.get("episodeId") or "").lower()
        try:
            story = load_episode_spec(
                episode_spec_path,
                expected_episode_id=expected_episode_id,
            )
        except EpisodeSpecError as exc:
            raise EpisodeQualityError(str(exc)) from exc

        raw_spec = self._read_object(episode_spec_path, "episode.json")
        raw_scenes = raw_spec.get("scenes")
        if not isinstance(raw_scenes, list) or len(raw_scenes) < 5:
            raise EpisodeQualityError("몰입 구조를 위해 Scene이 최소 5개 필요합니다.")

        evidence_ids = {
            str(item.get("id"))
            for item in evidence_payload.get("items", [])
            if isinstance(item, dict) and item.get("id")
        }
        if not evidence_ids:
            raise EpisodeQualityError("사용 가능한 Evidence ID가 없습니다.")

        for index, (raw_scene, beat) in enumerate(
            zip(raw_scenes, story.beats, strict=True),
            start=1,
        ):
            if len(beat.keywords) < 2:
                raise EpisodeQualityError(
                    f"scenes[{index}]의 미디어 검색어가 최소 2개 필요합니다."
                )
            scene_evidence_ids = raw_scene.get("evidenceIds")
            if not isinstance(scene_evidence_ids, list) or not scene_evidence_ids:
                raise EpisodeQualityError(
                    f"scenes[{index}]에 근거 Evidence ID가 필요합니다."
                )
            unknown_ids = {
                str(evidence_id)
                for evidence_id in scene_evidence_ids
                if str(evidence_id) not in evidence_ids
            }
            if unknown_ids:
                raise EpisodeQualityError(
                    f"scenes[{index}]에 알 수 없는 Evidence ID가 있습니다: "
                    + ", ".join(sorted(unknown_ids))
                )

        if "?" not in story.beats[-1].narration:
            raise EpisodeQualityError("마지막 Scene은 댓글을 유도하는 질문이어야 합니다.")

        self._validate_metadata(metadata_payload)
        allowed_source_urls = {
            str(item.get("source_url") or "").strip()
            for item in evidence_payload.get("items", [])
            if isinstance(item, dict)
        }
        metadata_sources = {
            str(source).strip() for source in metadata_payload.get("sources", [])
        }
        unknown_sources = metadata_sources - allowed_source_urls
        if unknown_sources:
            raise EpisodeQualityError(
                "metadata.sources에 검증되지 않은 URL이 있습니다: "
                + ", ".join(sorted(unknown_sources))
            )

        updated = copy.deepcopy(job_payload)
        artifacts = updated.setdefault("artifacts", {})
        artifacts["episodeSpec"] = episode_spec_path.as_posix()
        artifacts["metadata"] = metadata_path.as_posix()
        updated["status"] = "episode_ready"
        updated["nextAction"] = "build_timeline"
        updated["updatedAt"] = datetime.now(timezone.utc).isoformat()
        return updated

    @staticmethod
    def _read_object(path: Path, label: str) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise EpisodeQualityError(f"{label}을 읽지 못했습니다: {exc}") from exc
        if not isinstance(payload, dict):
            raise EpisodeQualityError(f"{label} 최상위 값은 객체여야 합니다.")
        return payload

    @staticmethod
    def _validate_metadata(payload: dict[str, Any]) -> None:
        for key in ("title", "description", "pinnedComment"):
            value = payload.get(key)
            if not isinstance(value, str) or not value.strip():
                raise EpisodeQualityError(f"metadata.{key}가 필요합니다.")
        tags = payload.get("tags")
        if not isinstance(tags, list) or len(tags) < 5:
            raise EpisodeQualityError("metadata.tags가 최소 5개 필요합니다.")
        sources = payload.get("sources")
        if not isinstance(sources, list) or len(sources) < 3:
            raise EpisodeQualityError("metadata.sources가 최소 3개 필요합니다.")


class TimelineQualityService:
    def validate_and_advance(
        self,
        *,
        job_payload: dict[str, Any],
        timeline_path: Path,
        media_queries_path: Path,
    ) -> dict[str, Any]:
        if job_payload.get("status") != "episode_ready":
            raise EpisodeQualityError(
                "episode_ready 상태의 작업만 Timeline 품질 검사를 할 수 있습니다."
            )

        timeline = EpisodeQualityService._read_object(
            timeline_path,
            "timeline.json",
        )
        media_queries = EpisodeQualityService._read_object(
            media_queries_path,
            "media_queries.json",
        )
        expected_episode_id = str(job_payload.get("episodeId") or "").lower()
        if str(timeline.get("episodeId") or "").lower() != expected_episode_id:
            raise EpisodeQualityError("Timeline episodeId가 Production Job과 다릅니다.")

        scenes = timeline.get("scenes")
        if not isinstance(scenes, list) or not scenes:
            raise EpisodeQualityError("Timeline Scene이 비어 있습니다.")
        for index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                raise EpisodeQualityError(f"Timeline scenes[{index}] 형식이 잘못됐습니다.")
            if scene.get("narration") != scene.get("caption"):
                raise EpisodeQualityError(
                    f"Timeline scenes[{index}]의 TTS 원문과 자막이 다릅니다."
                )

        query_scenes = media_queries.get("scenes")
        if not isinstance(query_scenes, list) or len(query_scenes) != len(scenes):
            raise EpisodeQualityError("Scene 수와 미디어 검색어 수가 다릅니다.")
        for index, query_scene in enumerate(query_scenes, start=1):
            if not isinstance(query_scene, dict) or not query_scene.get("primaryQuery"):
                raise EpisodeQualityError(
                    f"media_queries scenes[{index}]의 primaryQuery가 비어 있습니다."
                )

        updated = copy.deepcopy(job_payload)
        artifacts = updated.setdefault("artifacts", {})
        artifacts["timeline"] = timeline_path.as_posix()
        artifacts["mediaQueries"] = media_queries_path.as_posix()
        updated["status"] = "media_planned"
        updated["nextAction"] = "collect_media"
        updated["updatedAt"] = datetime.now(timezone.utc).isoformat()
        return updated
