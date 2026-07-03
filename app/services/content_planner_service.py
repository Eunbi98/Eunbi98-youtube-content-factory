import json
import logging
import re

from app.research import ResearchContextBuilder
from app.services.prompt_manager import PromptManager
from app.story import KoreanLanguageGuard, ScriptQAEngine, StoryDirector
from config.settings import MAX_CONTENT_LENGTH


logger = logging.getLogger(__name__)


class ContentPlannerService:
    def __init__(self, llm=None, prompt_manager=None):
        if llm is None:
            from app.services.ollama_service import OllamaService

            llm = OllamaService()

        self.llm = llm
        self.prompt_manager = prompt_manager or PromptManager()
        self.research_builder = ResearchContextBuilder()
        self.story_director = StoryDirector()
        self.script_qa = ScriptQAEngine()
        self.language_guard = KoreanLanguageGuard()

    def plan(self, article) -> dict:
        content = article.cleaned_content or article.content

        if not content:
            return self._empty_result()

        research_context = self.create_research_context(article, content)
        story_plan = self.create_story_plan(article, content, research_context)
        prompt_template = self.prompt_manager.load("content_planner_prompt.txt")
        prompt = (
            prompt_template
            .replace("{title}", article.title or "")
            .replace("{source}", article.source or "")
            .replace("{content}", content[:MAX_CONTENT_LENGTH])
        )
        prompt = self._append_planning_context(
            prompt=prompt,
            story_plan=story_plan,
            research_context=research_context,
        )

        response = self.llm.generate(prompt)
        json_text = self._extract_json(response)

        try:
            result = json.loads(json_text)
            return self._normalize_result(
                result,
                article=article,
                story_plan=story_plan,
                research_context=research_context,
            )
        except json.JSONDecodeError:
            repaired = self._repair_json(json_text)

            try:
                result = json.loads(repaired)
                return self._normalize_result(
                    result,
                    article=article,
                    story_plan=story_plan,
                    research_context=research_context,
                )
            except json.JSONDecodeError:
                return self._fallback_result(
                    response,
                    article=article,
                    story_plan=story_plan,
                    research_context=research_context,
                )

    def create_research_context(self, article, content: str | None = None) -> dict:
        source_text = (
            content
            or article.summary
            or article.cleaned_content
            or article.content
            or ""
        )
        context = self.research_builder.build(
            title=article.title or "",
            summary=source_text[:1500],
            source=article.source or "",
            url=getattr(article, "link", "") or "",
        )
        logger.info("Research Engine connected: topic=%s", context.get("topic", ""))
        return context

    def create_story_plan(
        self,
        article,
        content: str | None = None,
        research_context: dict | None = None,
    ) -> dict:
        source_text = (
            content
            or article.summary
            or article.cleaned_content
            or article.content
            or ""
        )

        research_summary = ""

        if research_context:
            research_summary = "\n".join([
                str(research_context.get("topic", "")),
                str(research_context.get("core_question", "")),
                *[str(item) for item in research_context.get("story_clues", [])],
                str(research_context.get("possible_resolution", "")),
            ])

        story_plan = self.story_director.create_story(
            title=article.title or "",
            summary=f"{source_text[:1000]}\n{research_summary}",
            source=article.source or "",
            url=getattr(article, "link", "") or "",
        )

        logger.info(
            "Story Engine connected: category=%s emotion=%s title=%s",
            story_plan.get("category", ""),
            story_plan.get("emotion", ""),
            article.title,
        )

        return story_plan

    def build_story_script(
        self,
        base_text: str,
        story_plan: dict,
        research_context: dict | None = None,
    ) -> str:
        hook = self._clean_script_line(str(story_plan.get("hook", "")))
        ending = self._clean_script_line(str(story_plan.get("ending", "")))
        middle_lines = self._research_script_lines(research_context)

        if not middle_lines:
            middle_lines = self._extract_subtitle_lines(base_text)

        script_lines = []

        if hook:
            script_lines.append(hook)

        script_lines.extend(self._select_middle_story_lines(middle_lines))

        if ending:
            script_lines.append(ending)

        raw_script = "\n".join(line for line in script_lines if line)
        polished_script = self.script_qa.polish_script(
            raw_script,
            protected_first=hook,
            protected_last=ending,
        )

        return self.language_guard.ensure_korean_script(
            script=polished_script,
            story_plan=story_plan,
        )

    def apply_story_engine_to_result(
        self,
        result: dict,
        article,
        story_plan: dict,
        research_context: dict | None = None,
    ) -> dict:
        return self._normalize_result(
            result,
            article=article,
            story_plan=story_plan,
            research_context=research_context,
        )

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

    def _normalize_result(
        self,
        result: dict,
        article=None,
        story_plan: dict | None = None,
        research_context: dict | None = None,
    ) -> dict:
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

        if research_context:
            default["research_context"] = research_context

        if story_plan:
            default = self._apply_story_engine(
                result=default,
                article=article,
                story_plan=story_plan,
                research_context=research_context,
            )

        default["hashtags"] = self._normalize_hashtags(
            default.get("hashtags", [])
        )
        default["scenes"] = self._normalize_scenes(
            default.get("scenes", []),
            default["script"],
        )

        return default

    def _append_planning_context(
        self,
        prompt: str,
        story_plan: dict,
        research_context: dict,
    ) -> str:
        story_structure = story_plan.get("story_structure", [])
        structure_text = " -> ".join(
            str(item.get("section", ""))
            for item in story_structure
            if isinstance(item, dict)
        )
        source_plan_text = "\n".join(
            f"- {item.get('source_type', '')}: {item.get('purpose', '')}"
            for item in research_context.get("source_plan", [])
            if isinstance(item, dict)
        )

        return f"""{prompt}

Research Engine v1 context:
- topic: {research_context.get("topic", "")}
- core_question: {research_context.get("core_question", "")}
- background_points: {research_context.get("background_points", [])}
- related_angles: {research_context.get("related_angles", [])}
- story_clues: {research_context.get("story_clues", [])}
- possible_resolution: {research_context.get("possible_resolution", "")}
- source_plan:
{source_plan_text}

Story Engine v1 plan:
- category: {story_plan.get("category", "")}
- emotion: {story_plan.get("emotion", "")}
- hook: {story_plan.get("hook", "")}
- structure: {structure_text}
- ending: {story_plan.get("ending", "")}

Required Shorts story flow:
1. Hook
2. 사건 제시
3. 왜 이상한지
4. 배경 또는 관련 사례
5. 현재까지 밝혀진 것
6. 남은 의문
7. 여운 있는 결말

Korean output rules:
- All summary, script, scenes.text, youtube title, and thumbnail text must be Korean.
- Translate and rewrite English source text into natural Korean.
- Do not output full English sentences.
- Koreanize proper nouns where possible, such as NASA -> 나사 and James Webb Space Telescope -> 제임스 웹 우주망원경.
- The first script sentence must be exactly the hook.
- The script must use the Research Engine context to add background, related cases, known facts, and remaining questions.
- The last script sentence must be exactly the ending.
- Write short Korean subtitle lines around 18-25 characters.
- Do not include stage directions such as 음악 삽입, 장면 전환, BGM, 효과음, 자막 표시, 화면 지시, 이미지 지시, 컷.
"""

    def _apply_story_engine(
        self,
        result: dict,
        article,
        story_plan: dict,
        research_context: dict | None = None,
    ) -> dict:
        source_text = ""

        if article is not None:
            source_text = (
                getattr(article, "summary", "")
                or getattr(article, "cleaned_content", "")
                or getattr(article, "content", "")
                or ""
            )

        draft_script = self._to_text(result.get("script", ""))
        base_text = draft_script or result.get("summary", "") or source_text

        result["category"] = story_plan.get(
            "category",
            result.get("category", ""),
        )
        result["emotion"] = story_plan.get(
            "emotion",
            result.get("emotion", ""),
        )
        result["hook"] = story_plan.get("hook", result.get("hook", ""))
        result["story_flow"] = [
            "hook",
            "incident",
            "strangeness",
            "background",
            "known_so_far",
            "remaining_question",
            "ending",
        ]
        result["script"] = self.build_story_script(
            base_text=base_text,
            story_plan=story_plan,
            research_context=research_context,
        )
        result["scenes"] = self.language_guard.sync_scenes_to_script(
            script=result["script"],
            previous_scenes=result.get("scenes", []),
        )

        return result

    def _research_script_lines(self, research_context: dict | None) -> list[str]:
        if not research_context:
            return []

        lines = []
        clues = [
            str(item)
            for item in research_context.get("story_clues", [])
            if str(item).strip()
        ]
        background = [
            str(item)
            for item in research_context.get("background_points", [])
            if str(item).strip()
        ]
        related = [
            str(item)
            for item in research_context.get("related_angles", [])
            if str(item).strip()
        ]
        resolution = str(research_context.get("possible_resolution", "")).strip()

        if clues:
            lines.append(clues[0])

        if len(clues) > 1:
            lines.append(clues[1])

        if background:
            lines.append(background[0])

        if related:
            lines.append(related[0])

        if resolution:
            lines.append(resolution)

        if len(clues) > 2:
            lines.append(clues[2])

        return lines

    def _select_middle_story_lines(self, lines: list[str]) -> list[str]:
        fallback_lines = [
            "사건은 작은 단서에서 시작됐습니다.",
            "하지만 그 의미는 바로 설명되지 않았습니다.",
            "현재까지 확인된 사실과 남은 질문이 함께 있습니다.",
        ]
        selected = [
            line
            for line in lines
            if line not in fallback_lines
        ]
        source_count = len(selected)
        selected = selected[:8]

        while (
            selected
            and source_count > len(selected)
            and not self._has_terminal_ending(selected[-1])
            and len(selected) < 10
        ):
            selected.append(lines[len(selected)])

        while len(selected) < 5:
            selected.append(fallback_lines[len(selected) % len(fallback_lines)])

        return selected

    def _has_terminal_ending(self, line: str) -> bool:
        return bool(re.search(r"[.!?。？！]$", line.strip()))

    def _extract_subtitle_lines(self, text: str) -> list[str]:
        return self.script_qa.polish_lines(
            [
                line.strip()
                for line in str(text or "").splitlines()
                if line.strip()
            ]
        )

    def _clean_script_line(self, line: str) -> str:
        line = re.sub(r"^\s*[-*\d.)]+\s*", "", line)
        line = re.sub(r"\s+", " ", line)
        return line.strip()

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

                duration = max(3, min(duration, 5))

                if text:
                    normalized.append({
                        "order": index,
                        "text": text,
                        "image_keyword": keyword,
                        "duration": duration,
                    })

        if normalized:
            return normalized

        return self.language_guard.sync_scenes_to_script(script)

    def _to_text(self, value):
        if isinstance(value, list):
            return "\n".join(
                str(item).strip()
                for item in value
                if str(item).strip()
            )

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
            "research_context": {},
            "summary": "",
            "script": "",
            "scenes": [],
            "youtube_title": "",
            "thumbnail_text": "",
            "hashtags": [],
        }

    def _fallback_result(
        self,
        response: str,
        article=None,
        story_plan: dict | None = None,
        research_context: dict | None = None,
    ) -> dict:
        clean_response = response.strip() if response else ""

        fallback = {
            "score": 30,
            "category": "other",
            "emotion": "curiosity",
            "reason": "AI 응답이 JSON 형식은 아니지만 콘텐츠 초안으로 사용할 수 있습니다.",
            "core_topic": "",
            "hook": "",
            "story_flow": [],
            "research_context": research_context or {},
            "summary": clean_response[:500],
            "script": clean_response[:1200],
            "scenes": self._normalize_scenes([], clean_response[:1200]),
            "youtube_title": "",
            "thumbnail_text": "",
            "hashtags": ["#해외뉴스", "#쇼츠"],
        }

        if story_plan:
            fallback = self._apply_story_engine(
                result=fallback,
                article=article,
                story_plan=story_plan,
                research_context=research_context,
            )
            fallback["scenes"] = self._normalize_scenes(
                fallback["scenes"],
                fallback["script"],
            )

        return fallback
