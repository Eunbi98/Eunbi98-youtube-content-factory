import json
import re
from pathlib import Path

from app.services.ollama_service import OllamaService


class ProducerService:
    def __init__(self):
        self.llm = OllamaService()
        self.prompt_path = Path("prompts/producer_prompt.txt")

    def produce(self, article) -> dict:
        content = article.cleaned_content or article.content

        if not content:
            return self._empty_result()

        prompt_template = self.prompt_path.read_text(encoding="utf-8")

        prompt = (
            prompt_template
            .replace("{title}", article.title)
            .replace("{source}", article.source)
            .replace("{content}", content[:2500])
        )

        response = self.llm.generate(prompt)

        json_text = self._extract_json(response)

        try:
            return json.loads(json_text)
        except json.JSONDecodeError:
            return self._fallback_result(response)

    def _extract_json(self, response: str) -> str:
        # ```json ... ``` 형태 제거
        match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)

        if match:
            return match.group(1).strip()

        # 그냥 ``` ... ``` 형태 제거
        match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)

        if match:
            return match.group(1).strip()

        # 응답 안에서 { ... } 부분만 추출
        start = response.find("{")
        end = response.rfind("}")

        if start != -1 and end != -1:
            return response[start:end + 1].strip()

        return response.strip()

    def _empty_result(self) -> dict:
        return {
            "score": 0,
            "category": "other",
            "reason": "",
            "summary": "",
            "script": "",
            "youtube_title": "",
            "thumbnail_text": "",
            "hook": ""
        }

    def _fallback_result(self, response: str) -> dict:
        return {
            "score": 0,
            "category": "other",
            "reason": "AI 응답을 JSON으로 변환하지 못했습니다.",
            "summary": response,
            "script": response,
            "youtube_title": "",
            "thumbnail_text": "",
            "hook": ""
        }