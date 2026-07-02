import json
import re

from app.services.ollama_service import OllamaService
from app.services.prompt_manager import PromptManager
from config.settings import MAX_CONTENT_LENGTH


class ContentPlannerService:
    def __init__(self):
        self.llm = OllamaService()
        self.prompt_manager = PromptManager()

    def plan(self, article) -> dict:
        content = article.cleaned_content or article.content

        if not content:
            return self._empty_result()

        prompt_template = self.prompt_manager.load(
            "content_planner_prompt.txt"
        )

        prompt = (
            prompt_template
            .replace("{title}", article.title or "")
            .replace("{source}", article.source or "")
            .replace("{content}", content[:MAX_CONTENT_LENGTH])
        )

        response = self.llm.generate(prompt)
        json_text = self._extract_json(response)

        try:
            result = json.loads(json_text)
            return self._normalize_result(result)

        except json.JSONDecodeError:
            repaired = self._repair_json(json_text)

            try:
                result = json.loads(repaired)
                return self._normalize_result(result)

            except json.JSONDecodeError:
                return self._fallback_result(response)

    def _extract_json(self, response: str) -> str:
        if not response:
            return ""

        response = response.strip()
        response = response.replace("```json", "")
        response = response.replace("```", "")

        start = response.find("{")
        end = response.rfind("}")

        if start != -1 and end != -1 and end > start:
            return response[start:end + 1].strip()

        return response.strip()

    def _repair_json(self, text: str) -> str:
        text = text.strip()
        text = re.sub(r",\s*}", "}", text)
        text = re.sub(r",\s*]", "]", text)
        text = text.replace("\t", " ")

        return text

    def _normalize_result(self, result: dict) -> dict:
        default = self._empty_result()
        default.update(result)

        try:
            default["score"] = int(default.get("score", 0))
        except ValueError:
            default["score"] = 0

        default["summary"] = self._to_text(default.get("summary", ""))
        default["script"] = self._to_text(default.get("script", ""))
        default["thumbnail_text"] = self._to_text(
            default.get("thumbnail_text", "")
        )

        default["hashtags"] = self._normalize_hashtags(
            default.get("hashtags", [])
        )

        default["scenes"] = self._normalize_scenes(
            default.get("scenes", []),
            default["script"]
        )

        return default

    def _normalize_hashtags(self, hashtags):
        if isinstance(hashtags, str):
            return [
                tag.strip()
                for tag in hashtags.split()
                if tag.strip()
            ]

        if isinstance(hashtags, list):
            return [
                str(tag).strip()
                for tag in hashtags
                if str(tag).strip()
            ]

        return []

    def _normalize_scenes(self, scenes, script: str):
        normalized = []

        if isinstance(scenes, list):
            for index, scene in enumerate(scenes, start=1):
                if not isinstance(scene, dict):
                    continue

                text = str(scene.get("text", "")).strip()
                keyword = str(scene.get("image_keyword", "")).strip()

                try:
                    duration = int(scene.get("duration", 4))
                except ValueError:
                    duration = 4

                if duration < 3:
                    duration = 3

                if duration > 5:
                    duration = 5

                if text:
                    normalized.append({
                        "order": index,
                        "text": text,
                        "image_keyword": keyword,
                        "duration": duration
                    })

        if normalized:
            return normalized

        lines = [
            line.strip()
            for line in script.splitlines()
            if line.strip()
        ]

        fallback_scenes = []

        for index, line in enumerate(lines[:5], start=1):
            fallback_scenes.append({
                "order": index,
                "text": line,
                "image_keyword": "",
                "duration": 4
            })

        return fallback_scenes

    def _to_text(self, value):
        if isinstance(value, list):
            return "\n".join(str(item).strip() for item in value if str(item).strip())

        return str(value).strip()

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
            "scenes": [],
            "youtube_title": "",
            "thumbnail_text": "",
            "hashtags": []
        }

    def _fallback_result(self, response: str) -> dict:
        clean_response = response.strip() if response else ""

        return {
            "score": 30,
            "category": "other",
            "emotion": "curiosity",
            "reason": "AI 응답이 JSON 형식은 아니지만 콘텐츠 초안으로 활용 가능합니다.",
            "core_topic": "",
            "hook": "",
            "story_flow": [],
            "summary": clean_response[:500],
            "script": clean_response[:1200],
            "scenes": self._normalize_scenes([], clean_response[:1200]),
            "youtube_title": "",
            "thumbnail_text": "",
            "hashtags": ["#해외뉴스", "#쇼츠"]
        }