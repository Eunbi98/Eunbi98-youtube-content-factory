from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.story import StoryDirector


def main() -> None:
    samples = [
        {
            "title": "NASA's Webb Telescope Spots a Mysterious Planet Signal",
            "summary": (
                "제임스 웹 우주망원경이 먼 행성 주변에서 알 수 없는 대기 신호를 "
                "포착했다. 과학자들은 이 신호가 행성 형성 과정의 새로운 단서가 "
                "될 수 있다고 보고 있다."
            ),
            "source": "NASA",
            "url": "https://example.com/space-signal",
        },
        {
            "title": "AI Robot Learns a New Skill After Watching Humans",
            "summary": (
                "연구진은 인공지능 로봇이 사람의 행동을 관찰한 뒤 복잡한 작업을 "
                "스스로 따라 하는 기술을 공개했다. 이 기술은 제조와 돌봄 현장에 "
                "큰 변화를 만들 가능성이 있다."
            ),
            "source": "Tech Daily",
            "url": "https://example.com/ai-robot",
        },
        {
            "title": "Rescuers Save Whale Trapped Near the Coast",
            "summary": (
                "해안가 그물에 걸린 고래가 구조대와 시민들의 도움으로 무사히 "
                "바다로 돌아갔다. 현장에 있던 사람들은 고래가 헤엄쳐 나가는 "
                "순간에 큰 감동을 받았다."
            ),
            "source": "Ocean News",
            "url": "https://example.com/whale-rescue",
        },
    ]

    director = StoryDirector()
    results = [director.create_story_from_mapping(sample) for sample in samples]

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
