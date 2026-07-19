from __future__ import annotations

from typing import Any

from projects.ai.github_models_client import GithubModelsClient, GithubModelsError
from projects.production.openai_episode_provider import EPISODE_PACKAGE_SCHEMA


class EpisodeProviderError(RuntimeError):
    """GitHub Models Episode/Metadata 생성 오류."""


class GithubModelsEpisodeProvider:
    def __init__(self, *, client: GithubModelsClient) -> None:
        self._client = client

    @classmethod
    def from_environment(cls) -> "GithubModelsEpisodeProvider":
        return cls(client=GithubModelsClient.from_environment())

    def build(
        self,
        *,
        job_payload: dict[str, Any],
        evidence_payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_inputs(job_payload, evidence_payload)
        system = (
            "Create one upload-ready Korean YouTube Shorts episode package from "
            "only the verified evidence in the input. Make exactly 6 scenes in "
            "this order: hook, answer, story, fact, fact, ending. Narration is "
            "also the exact TTS and caption text, so never provide separate "
            "caption wording. Keep total narration suitable for roughly 45 to "
            "60 seconds. Start with a strong first sentence, add one clear "
            "reveal or tension turn in the middle, and end with a concrete "
            "question containing a question mark. Every factual scene must cite "
            "one or more evidenceIds that exist in the input. Never add a date, "
            "number, cause, quotation, or conclusion not supported by those "
            "items. State uncertainty plainly. Use 2 to 4 precise English-first "
            "media search queries per scene, aimed at official, Wikimedia, NASA, "
            "museum, archive, location, object, or scientific visuals. Metadata "
            "must include an accurate title, description, 5 to 15 tags, a pinned "
            "comment that repeats the ending question, and at least 3 distinct "
            "source URLs copied exactly from evidence. Do not include unsupported "
            "sensational claims. Return only the structured JSON result."
        )
        try:
            result = self._client.complete_json(
                system=system,
                user_payload={
                    "episodeId": job_payload["episodeId"],
                    "category": job_payload["category"],
                    "selectedTopic": job_payload["selectedTopic"],
                    "evidence": {
                        "summary": evidence_payload.get("summary", ""),
                        "uncertainties": evidence_payload.get("uncertainties", []),
                        "items": evidence_payload.get("items", []),
                    },
                },
                schema_name="factory_episode_package",
                schema=EPISODE_PACKAGE_SCHEMA,
            )
        except GithubModelsError as exc:
            raise EpisodeProviderError(str(exc)) from exc
        self._normalize_render_theme(result)
        self._validate_identity(result, job_payload)
        return result

    @staticmethod
    def _normalize_render_theme(result: dict[str, Any]) -> None:
        episode = result.get("episode")
        if not isinstance(episode, dict):
            return

        theme = episode.get("theme")
        if isinstance(theme, dict):
            theme["captionColor"] = "#FFFFFF"

    @staticmethod
    def _validate_inputs(
        job_payload: dict[str, Any],
        evidence_payload: dict[str, Any],
    ) -> None:
        if job_payload.get("status") != "evidence_ready":
            raise EpisodeProviderError(
                "Episode 생성은 evidence_ready 상태에서만 가능합니다."
            )
        if evidence_payload.get("status") != "verified":
            raise EpisodeProviderError("검증 완료된 Evidence가 필요합니다.")

    @staticmethod
    def _validate_identity(
        result: dict[str, Any],
        job_payload: dict[str, Any],
    ) -> None:
        episode = result.get("episode")
        metadata = result.get("metadata")
        if not isinstance(episode, dict) or not isinstance(metadata, dict):
            raise EpisodeProviderError("episode 또는 metadata 결과가 없습니다.")
        expected_id = str(job_payload.get("episodeId") or "").lower()
        for label, payload in (("episode", episode), ("metadata", metadata)):
            if str(payload.get("episodeId") or "").lower() != expected_id:
                raise EpisodeProviderError(
                    f"{label}.episodeId가 Production Job과 다릅니다."
                )
        expected_category = str(job_payload.get("category") or "").lower()
        if str(episode.get("channel") or "").lower() != expected_category:
            raise EpisodeProviderError(
                "episode.channel이 Production Job category와 다릅니다."
            )
