from __future__ import annotations

import json
import os
from typing import Any, Callable

from projects.production.metadata_style import METADATA_STYLE_INSTRUCTIONS


class EpisodeProviderError(RuntimeError):
    """Episode/Metadata 생성 Provider 요청 또는 응답 오류."""


Transport = Callable[[dict[str, Any]], dict[str, Any]]


THEME_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "backgroundColor": {"type": "string"},
        "titleColor": {"type": "string"},
        "captionColor": {"type": "string"},
        "accentColor": {"type": "string"},
    },
    "required": [
        "backgroundColor",
        "titleColor",
        "captionColor",
        "accentColor",
    ],
    "additionalProperties": False,
}


SCENE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["hook", "answer", "story", "fact", "ending"],
        },
        "title": {"type": "string"},
        "narration": {"type": "string"},
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 2,
            "maxItems": 4,
        },
        "evidenceIds": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
    },
    "required": ["type", "title", "narration", "keywords", "evidenceIds"],
    "additionalProperties": False,
}


EPISODE_PACKAGE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "episode": {
            "type": "object",
            "properties": {
                "version": {"type": "string"},
                "episodeId": {"type": "string"},
                "channel": {
                    "type": "string",
                    "enum": ["mystery", "science", "history", "space"],
                },
                "mediaSource": {"type": "string"},
                "title": {"type": "string"},
                "theme": THEME_SCHEMA,
                "scenes": {
                    "type": "array",
                    "items": SCENE_SCHEMA,
                    "minItems": 6,
                    "maxItems": 6,
                },
            },
            "required": [
                "version",
                "episodeId",
                "channel",
                "mediaSource",
                "title",
                "theme",
                "scenes",
            ],
            "additionalProperties": False,
        },
        "metadata": {
            "type": "object",
            "properties": {
                "episodeId": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 5,
                    "maxItems": 15,
                },
                "pinnedComment": {"type": "string"},
                "sources": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 2,
                },
            },
            "required": [
                "episodeId",
                "title",
                "description",
                "tags",
                "pinnedComment",
                "sources",
            ],
            "additionalProperties": False,
        },
    },
    "required": ["episode", "metadata"],
    "additionalProperties": False,
}


class OpenAIEpisodeProvider:
    API_URL = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gpt-5.6",
        transport: Transport | None = None,
        timeout_seconds: float = 240.0,
    ) -> None:
        if not api_key.strip():
            raise EpisodeProviderError("OPENAI_API_KEY가 비어 있습니다.")
        self._api_key = api_key.strip()
        self._model = model.strip() or "gpt-5.6"
        self._timeout_seconds = timeout_seconds
        self._transport = transport or self._request

    @classmethod
    def from_environment(cls) -> "OpenAIEpisodeProvider":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise EpisodeProviderError(
                "OPENAI_API_KEY 환경변수가 없습니다. "
                "GitHub Secrets에 OPENAI_API_KEY를 설정해 주세요."
            )
        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_STORY_MODEL", "gpt-5.6"),
        )

    def build(
        self,
        *,
        job_payload: dict[str, Any],
        evidence_payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._validate_inputs(job_payload, evidence_payload)
        response = self._transport(
            self._build_request(job_payload, evidence_payload)
        )
        result = self._extract_result(response)
        self._validate_identity(result, job_payload)
        return result

    def _build_request(
        self,
        job_payload: dict[str, Any],
        evidence_payload: dict[str, Any],
    ) -> dict[str, Any]:
        input_payload = {
            "episodeId": job_payload["episodeId"],
            "category": job_payload["category"],
            "selectedTopic": job_payload["selectedTopic"],
            "evidence": {
                "summary": evidence_payload.get("summary", ""),
                "uncertainties": evidence_payload.get("uncertainties", []),
                "items": evidence_payload.get("items", []),
            },
        }
        instructions = (
            "Create one upload-ready Korean YouTube Shorts episode package from "
            "only the verified evidence in the input. Make exactly 6 scenes in "
            "this order: hook, answer, story, fact, fact, ending. Narration is "
            "also the exact TTS and caption text, so never provide separate "
            "caption wording. Keep the total narration suitable for roughly "
            "45 to 60 seconds. Strengthen the first sentence, keep one clear "
            "reveal or tension turn in the middle, and end with a concrete "
            "question containing a question mark. Every factual scene must cite "
            "one or more evidenceIds that exist in the input. Never add a date, "
            "number, cause, quotation, or conclusion not supported by those "
            "items. State uncertainty plainly. Use 2 to 4 precise English-first "
            "media search queries per scene, aimed at official, Wikimedia, NASA, "
            "museum, archive, location, object, or scientific visuals. Titles "
            "should be concise Korean with an intentional line break when useful. "
            "Metadata must include an accurate title, description, 5 to 15 tags, "
            "a pinned comment that repeats the ending question, and at least 2 "
            "distinct source URLs copied exactly from evidence. Do not include "
            "unsupported sensational claims. "
            + METADATA_STYLE_INSTRUCTIONS
            + " Return JSON only through the schema."
        )
        return {
            "model": self._model,
            "instructions": instructions,
            "input": json.dumps(input_payload, ensure_ascii=False),
            "reasoning": {"effort": "high"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "factory_episode_package",
                    "strict": True,
                    "schema": EPISODE_PACKAGE_SCHEMA,
                }
            },
            "store": False,
        }

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            import requests
        except ImportError as exc:
            raise EpisodeProviderError(
                "requests 의존성이 설치되지 않았습니다."
            ) from exc

        try:
            response = requests.post(
                self.API_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise EpisodeProviderError(f"OpenAI API 요청 실패: {exc}") from exc

        if not response.ok:
            raise EpisodeProviderError(
                "OpenAI API가 오류를 반환했습니다. "
                f"HTTP {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise EpisodeProviderError(
                "OpenAI API 응답이 JSON이 아닙니다."
            ) from exc
        if not isinstance(data, dict):
            raise EpisodeProviderError("OpenAI API 응답 형식이 올바르지 않습니다.")
        return data

    @staticmethod
    def _extract_result(response: dict[str, Any]) -> dict[str, Any]:
        if response.get("status") not in {None, "completed"}:
            raise EpisodeProviderError(
                f"OpenAI 응답이 완료되지 않았습니다: {response.get('status')}"
            )
        output = response.get("output")
        if not isinstance(output, list):
            raise EpisodeProviderError("OpenAI 응답에 output 배열이 없습니다.")

        for output_item in output:
            if not isinstance(output_item, dict) or output_item.get("type") != "message":
                continue
            content = output_item.get("content")
            if not isinstance(content, list):
                continue
            for content_item in content:
                if not isinstance(content_item, dict):
                    continue
                if content_item.get("type") == "refusal":
                    raise EpisodeProviderError(
                        "Episode 생성 요청이 거부됐습니다: "
                        + str(content_item.get("refusal") or "")
                    )
                if content_item.get("type") != "output_text":
                    continue
                try:
                    result = json.loads(str(content_item.get("text") or ""))
                except json.JSONDecodeError as exc:
                    raise EpisodeProviderError(
                        "Structured Output을 JSON으로 읽지 못했습니다."
                    ) from exc
                if not isinstance(result, dict):
                    raise EpisodeProviderError(
                        "Episode 결과 최상위 값은 객체여야 합니다."
                    )
                return result
        raise EpisodeProviderError("OpenAI 응답에 결과 텍스트가 없습니다.")

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
            actual_id = str(payload.get("episodeId") or "").lower()
            if actual_id != expected_id:
                raise EpisodeProviderError(
                    f"{label}.episodeId가 Production Job과 다릅니다."
                )
        expected_category = str(job_payload.get("category") or "").lower()
        if str(episode.get("channel") or "").lower() != expected_category:
            raise EpisodeProviderError(
                "episode.channel이 Production Job category와 다릅니다."
            )
