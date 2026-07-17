from __future__ import annotations

import json
import os
from typing import Any, Callable


class EvidenceProviderError(RuntimeError):
    """외부 Evidence Provider 요청 또는 응답 오류."""


Transport = Callable[[dict[str, Any]], dict[str, Any]]


EVIDENCE_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "status": {
            "type": "string",
            "enum": ["complete", "insufficient"],
        },
        "summary": {"type": "string"},
        "uncertainties": {
            "type": "array",
            "items": {"type": "string"},
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "claim": {"type": "string"},
                    "source_name": {"type": "string"},
                    "source_url": {"type": "string"},
                    "source_tier": {
                        "type": "string",
                        "enum": ["official", "academic", "reference", "news"],
                    },
                    "evidence_type": {
                        "type": "string",
                        "enum": ["fact", "case", "counterpoint", "timeline"],
                    },
                    "published_at": {"type": "string"},
                    "keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                    },
                },
                "required": [
                    "title",
                    "claim",
                    "source_name",
                    "source_url",
                    "source_tier",
                    "evidence_type",
                    "published_at",
                    "keywords",
                ],
                "additionalProperties": False,
            },
        },
    },
    "required": ["status", "summary", "uncertainties", "items"],
    "additionalProperties": False,
}


class OpenAIEvidenceProvider:
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
            raise EvidenceProviderError("OPENAI_API_KEY가 비어 있습니다.")
        self._api_key = api_key.strip()
        self._model = model.strip() or "gpt-5.6"
        self._timeout_seconds = timeout_seconds
        self._transport = transport or self._request

    @classmethod
    def from_environment(cls) -> "OpenAIEvidenceProvider":
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise EvidenceProviderError(
                "OPENAI_API_KEY 환경변수가 없습니다. "
                "GitHub Secrets 또는 서버 비밀값으로 설정해 주세요."
            )
        return cls(
            api_key=api_key,
            model=os.getenv("OPENAI_RESEARCH_MODEL", "gpt-5.6"),
        )

    @property
    def model(self) -> str:
        return self._model

    def collect(self, job_payload: dict[str, Any]) -> dict[str, Any]:
        self._validate_job(job_payload)
        response = self._transport(self._build_request(job_payload))
        result, citations = self._extract_result(response)
        result["citations"] = citations
        result["provider"] = "openai_responses_web_search"
        result["model"] = self._model
        return result

    def _build_request(self, job_payload: dict[str, Any]) -> dict[str, Any]:
        topic = job_payload["selectedTopic"]["topic"]
        category = job_payload["category"]
        research_plan = job_payload["researchPlan"]
        prompt_data = {
            "episodeId": job_payload["episodeId"],
            "category": category,
            "topic": topic,
            "angle": job_payload["selectedTopic"].get("angle", ""),
            "questions": research_plan.get("questions", []),
            "queries": research_plan.get("queries", []),
            "sourceSeeds": research_plan.get("sourceSeeds", []),
        }
        instructions = (
            "You research short-form Korean educational videos. "
            "Search the live web before answering. Prefer primary official or "
            "academic sources, then established reference and news sources. "
            "Return Korean claims that are each supported by the source_url in "
            "the same item. Collect 4 to 6 non-duplicate items from at least "
            "3 independent domains. Include at least one official or academic "
            "item and one counterpoint or uncertainty. Do not turn speculation "
            "into fact. If these requirements cannot be met, return status "
            "insufficient and only the evidence you could verify. Do not invent "
            "URLs, dates, numbers, quotations, or findings. Use an empty string "
            "when a publication date is unavailable."
        )
        return {
            "model": self._model,
            "instructions": instructions,
            "input": json.dumps(prompt_data, ensure_ascii=False),
            "tools": [{"type": "web_search"}],
            "tool_choice": "required",
            "reasoning": {"effort": "high"},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "factory_evidence_result",
                    "strict": True,
                    "schema": EVIDENCE_SCHEMA,
                }
            },
            "store": False,
        }

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            import requests
        except ImportError as exc:
            raise EvidenceProviderError(
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
            raise EvidenceProviderError(f"OpenAI API 요청 실패: {exc}") from exc

        if not response.ok:
            raise EvidenceProviderError(
                "OpenAI API가 오류를 반환했습니다. "
                f"HTTP {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise EvidenceProviderError(
                "OpenAI API 응답이 JSON이 아닙니다."
            ) from exc
        if not isinstance(data, dict):
            raise EvidenceProviderError("OpenAI API 응답 형식이 올바르지 않습니다.")
        return data

    @staticmethod
    def _extract_result(
        response: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, str]]]:
        if response.get("status") not in {None, "completed"}:
            raise EvidenceProviderError(
                f"OpenAI 응답이 완료되지 않았습니다: {response.get('status')}"
            )

        output = response.get("output")
        if not isinstance(output, list):
            raise EvidenceProviderError("OpenAI 응답에 output 배열이 없습니다.")

        text_value: str | None = None
        citations: list[dict[str, str]] = []
        seen_urls: set[str] = set()
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
                    raise EvidenceProviderError(
                        f"Evidence 요청이 거부됐습니다: {content_item.get('refusal', '')}"
                    )
                if content_item.get("type") != "output_text":
                    continue
                text_value = str(content_item.get("text") or "")
                annotations = content_item.get("annotations")
                if not isinstance(annotations, list):
                    continue
                for annotation in annotations:
                    if not isinstance(annotation, dict):
                        continue
                    url = str(annotation.get("url") or "").strip()
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    citations.append(
                        {
                            "url": url,
                            "title": str(annotation.get("title") or "").strip(),
                        }
                    )

        if not text_value:
            raise EvidenceProviderError("OpenAI 응답에 결과 텍스트가 없습니다.")
        try:
            result = json.loads(text_value)
        except json.JSONDecodeError as exc:
            raise EvidenceProviderError(
                "Structured Output을 JSON으로 읽지 못했습니다."
            ) from exc
        if not isinstance(result, dict):
            raise EvidenceProviderError("Evidence 결과 최상위 값은 객체여야 합니다.")
        return result, citations

    @staticmethod
    def _validate_job(job_payload: dict[str, Any]) -> None:
        if job_payload.get("status") != "research_planned":
            raise EvidenceProviderError(
                "Evidence 수집은 research_planned 상태에서만 가능합니다."
            )
        if not isinstance(job_payload.get("selectedTopic"), dict):
            raise EvidenceProviderError("Production Job의 selectedTopic이 없습니다.")
        if not isinstance(job_payload.get("researchPlan"), dict):
            raise EvidenceProviderError("Production Job의 researchPlan이 없습니다.")
