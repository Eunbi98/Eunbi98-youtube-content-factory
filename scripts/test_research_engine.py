from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.research import ResearchContextBuilder


def main() -> None:
    samples = [
        {
            "title": "NASA Webb telescope detects mysterious signal",
            "summary": (
                "제임스 웹 우주망원경이 먼 행성 주변에서 설명이 필요한 신호를 "
                "포착했다. 연구진은 후속 관측으로 의미를 확인하려 한다."
            ),
            "source": "NASA",
            "url": "https://example.com/webb-signal",
        },
        {
            "title": "AI robot learns new skill after watching humans",
            "summary": (
                "인공지능 로봇이 사람의 행동을 보고 복잡한 작업을 따라 하는 "
                "기술이 공개됐다. 현장 적용 가능성과 안전 기준이 함께 논의된다."
            ),
            "source": "Tech Daily",
            "url": "https://example.com/ai-robot",
        },
        {
            "title": "Rescuers save whale trapped near coast",
            "summary": (
                "해안가 그물에 걸린 고래가 구조대와 시민들의 도움으로 "
                "바다로 돌아갔다. 해양 쓰레기 관리의 중요성이 다시 주목받았다."
            ),
            "source": "Ocean News",
            "url": "https://example.com/whale-rescue",
        },
    ]
    builder = ResearchContextBuilder()
    results = [builder.build(**sample) for sample in samples]

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
