import json
import re

from app.services.ollama_service import OllamaService
from app.services.prompt_manager import PromptManager


class ContentPlannerService:
    def __init__(self):
        self.llm = OllamaService()
        self.prompt_manager = PromptManager()

    def plan(self, article) -> dict:
        content = article.cleaned_content or article.content

        if not content:
            return self._empty_result()

        prompt_template = self.prompt_manager.load("content_planner_prompt.txt")

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
        match = re.search(r"```json\s*(.*?)\s*```", response, re.DOTALL)

        if match:
            return match.group(1).strip()

        match = re.search(r"```\s*(.*?)\s*```", response, re.DOTALL)

        if match:
            return match.group(1).strip()

        start = response.find("{")
        end = response.rfind("}")

        if start != -1 and end != -1:
            return response[start:end + 1].strip()

        return response.strip()

    def _empty_result(self) -> dict:
        return {
            "score": 0,
            "category": "other",
            "emotion": "",
            "reason": "",
            "core_topic": "",
            "hook": "",
            "story_flow": [],
            "summary": "",
            "script": "",
            "youtube_title": "",
            "thumbnail_text": "",
            "hashtags": []
        }

    def _fallback_result(self, response: str) -> dict:
        return {
            "score": 0,
            "category": "other",
            "emotion": "",
            "reason": "AI 응답을 JSON으로 변환하지 못했습니다.",
            "core_topic": "",
            "hook": "",
            "story_flow": [],
            "summary": response,
            "script": response,
            "youtube_title": "",
            "thumbnail_text": "",
            "hashtags": []
        }