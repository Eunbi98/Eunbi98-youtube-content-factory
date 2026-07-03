from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.content_planner_service import ContentPlannerService


class FakeLLM:
    def generate(self, prompt: str) -> str:
        return json.dumps(
            {
                "score": 80,
                "summary": "",
                "script": [],
                "scenes": [],
                "hashtags": ["#뉴스", "#쇼츠"],
            },
            ensure_ascii=False,
        )


def main() -> None:
    samples = [
        SimpleNamespace(
            title="NASA Webb telescope detects mysterious signal",
            source="NASA",
            link="https://example.com/webb-signal",
            summary="",
            cleaned_content=(
                "제임스 웹 우주망원경이 먼 행성 주변에서 설명이 필요한 신호를 "
                "포착했다. 연구진은 이 신호가 행성 형성 과정이나 대기 성분을 "
                "이해하는 단서가 될 수 있다고 보고 있다."
            ),
            content="",
        ),
        SimpleNamespace(
            title="AI robot learns new skill after watching humans",
            source="Tech Daily",
            link="https://example.com/ai-robot",
            summary="",
            cleaned_content=(
                "인공지능 로봇이 사람의 행동을 관찰한 뒤 복잡한 작업을 따라 하는 "
                "기술이 공개됐다. 제조와 돌봄 현장에 활용될 가능성이 있지만 "
                "안전 기준도 함께 필요하다는 지적이 나온다."
            ),
            content="",
        ),
        SimpleNamespace(
            title="Rescuers save whale trapped near coast",
            source="Ocean News",
            link="https://example.com/whale-rescue",
            summary="",
            cleaned_content=(
                "해안가 그물에 걸린 고래가 구조대와 시민들의 도움으로 무사히 "
                "바다로 돌아갔다. 구조대는 해양 쓰레기 관리가 중요하다고 전했다."
            ),
            content="",
        ),
    ]
    service = ContentPlannerService(llm=FakeLLM())
    outputs = []

    for article in samples:
        result = service.plan(article)
        research_context = result.get("research_context", {})
        outputs.append({
            "title": article.title,
            "research_topic": research_context.get("topic", ""),
            "core_question": research_context.get("core_question", ""),
            "story_flow": result.get("story_flow", []),
            "script": result.get("script", ""),
        })

    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
