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
                "scenes": [
                    {
                        "order": 1,
                        "text": "draft",
                        "image_keyword": "news scene",
                        "duration": 4,
                    }
                ],
                "hashtags": ["#뉴스", "#쇼츠"],
            },
            ensure_ascii=False,
        )


def main() -> None:
    samples = [
        SimpleNamespace(
            title="NASA's Webb Telescope Spots a Mysterious Planet Signal",
            source="NASA",
            link="https://example.com/space-signal",
            summary="",
            cleaned_content=(
                "제임스 웹 우주망원경이 먼 행성 주변에서 알 수 없는 대기 신호를 "
                "포착했다. 과학자들은 이 신호가 행성 형성 과정의 새로운 단서가 "
                "될 수 있다고 보고 있다. 다음 관측 결과에 따라 해석이 달라질 수 있다."
            ),
            content="",
        ),
        SimpleNamespace(
            title="AI Robot Learns a New Skill After Watching Humans",
            source="Tech Daily",
            link="https://example.com/ai-robot",
            summary="",
            cleaned_content=(
                "연구진은 인공지능 로봇이 사람의 행동을 관찰한 뒤 복잡한 작업을 "
                "스스로 따라 하는 기술을 공개했다. 이 기술은 제조와 돌봄 현장에서 "
                "활용될 가능성이 있다. 전문가들은 안전 기준도 함께 필요하다고 말한다."
            ),
            content="",
        ),
        SimpleNamespace(
            title="Rescuers Save Whale Trapped Near the Coast",
            source="Ocean News",
            link="https://example.com/whale-rescue",
            summary="",
            cleaned_content=(
                "해안가 그물에 걸린 고래가 구조대와 시민들의 도움으로 무사히 "
                "바다로 돌아갔다. 현장에 있던 사람들은 고래가 헤엄쳐 나가는 "
                "순간에 큰 감동을 받았다. 구조대는 해양 쓰레기 관리가 중요하다고 전했다."
            ),
            content="",
        ),
    ]

    service = ContentPlannerService(llm=FakeLLM())
    outputs = []

    for article in samples:
        normalized = service.plan(article)

        outputs.append({
            "title": article.title,
            "category": normalized["category"],
            "emotion": normalized["emotion"],
            "script": normalized["script"],
        })

    print(json.dumps(outputs, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
