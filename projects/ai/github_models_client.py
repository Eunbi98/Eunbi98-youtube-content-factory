from __future__ import annotations

import json
import os
from typing import Any, Callable


class GithubModelsError(RuntimeError):
    """GitHub Models 요청 또는 응답 오류."""


Transport = Callable[[dict[str, Any]], dict[str, Any]]


class GithubModelsClient:
    API_URL = "https://models.github.ai/inference/chat/completions"

    def __init__(
        self,
        *,
        token: str,
        model: str = "openai/gpt-4.1",
        transport: Transport | None = None,
        timeout_seconds: float = 240.0,
    ) -> None:
        if not token.strip():
            raise GithubModelsError("GITHUB_MODELS_TOKEN이 비어 있습니다.")
        self._token = token.strip()
        self._model = model.strip() or "openai/gpt-4.1"
        self._timeout_seconds = timeout_seconds
        self._transport = transport or self._request

    @classmethod
    def from_environment(
        cls,
        *,
        timeout_seconds: float = 240.0,
    ) -> "GithubModelsClient":
        token = (
            os.getenv("GITHUB_MODELS_TOKEN", "").strip()
            or os.getenv("GITHUB_TOKEN", "").strip()
        )
        if not token:
            raise GithubModelsError(
                "GITHUB_MODELS_TOKEN 환경변수가 없습니다. "
                "GitHub Actions에서는 github.token을 전달해 주세요."
            )
        return cls(
            token=token,
            model=os.getenv("GITHUB_MODELS_MODEL", "openai/gpt-4.1"),
            timeout_seconds=timeout_seconds,
        )

    @property
    def model(self) -> str:
        return self._model

    def complete_json(
        self,
        *,
        system: str,
        user_payload: dict[str, Any],
        schema_name: str,
        schema: dict[str, Any],
        max_tokens: int = 4000,
    ) -> dict[str, Any]:
        request = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": schema,
                },
            },
            "temperature": 0.2,
            "max_tokens": max_tokens,
        }
        response = self._transport(request)
        return self._extract_json(response)

    def _request(self, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            import requests
        except ImportError as exc:
            raise GithubModelsError(
                "requests 의존성이 설치되지 않았습니다."
            ) from exc

        try:
            response = requests.post(
                self.API_URL,
                headers={
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {self._token}",
                    "X-GitHub-Api-Version": "2022-11-28",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as exc:
            raise GithubModelsError(f"GitHub Models 요청 실패: {exc}") from exc

        if not response.ok:
            detail = ""
            try:
                detail = str(response.json().get("message") or "")
            except (ValueError, AttributeError):
                detail = ""
            if response.status_code == 429:
                raise GithubModelsError(
                    "GitHub Models 무료 사용 한도에 도달했습니다. "
                    "유료 전환 없이 한도가 초기화된 뒤 다시 실행해 주세요."
                )
            raise GithubModelsError(
                "GitHub Models가 오류를 반환했습니다. "
                f"HTTP {response.status_code}{': ' + detail if detail else ''}"
            )
        try:
            data = response.json()
        except ValueError as exc:
            raise GithubModelsError(
                "GitHub Models 응답이 JSON이 아닙니다."
            ) from exc
        if not isinstance(data, dict):
            raise GithubModelsError("GitHub Models 응답 형식이 올바르지 않습니다.")
        return data

    @staticmethod
    def _extract_json(response: dict[str, Any]) -> dict[str, Any]:
        choices = response.get("choices")
        if not isinstance(choices, list) or not choices:
            raise GithubModelsError("GitHub Models 응답에 choices가 없습니다.")
        first = choices[0]
        if not isinstance(first, dict):
            raise GithubModelsError("GitHub Models choice 형식이 잘못됐습니다.")
        message = first.get("message")
        if not isinstance(message, dict):
            raise GithubModelsError("GitHub Models message가 없습니다.")
        content = message.get("content")
        if not isinstance(content, str) or not content.strip():
            refusal = str(message.get("refusal") or "").strip()
            if refusal:
                raise GithubModelsError(f"GitHub Models 요청이 거부됐습니다: {refusal}")
            raise GithubModelsError("GitHub Models 결과 텍스트가 없습니다.")
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise GithubModelsError(
                "GitHub Models Structured Output을 읽지 못했습니다."
            ) from exc
        if not isinstance(result, dict):
            raise GithubModelsError("GitHub Models 결과 최상위 값은 객체여야 합니다.")
        return result
