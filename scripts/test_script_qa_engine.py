from __future__ import annotations

import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.story import ScriptQAEngine


def main() -> None:
    qa = ScriptQAEngine()
    samples = [
        {
            "name": "auxiliary_split",
            "script": (
                "과학자들이 하늘에서 이상한 신호를 포착했습니다.\n"
                "(음악 삽입) 제임스 웹 우주망원경이 먼 행성 주변에서 알 수\n"
                "없는 대기 신호를 포착했다.\n"
                "다음 관측이 이 질문의 방향을 바꿀지도 모릅니다."
            ),
            "first": "과학자들이 하늘에서 이상한 신호를 포착했습니다.",
            "last": "다음 관측이 이 질문의 방향을 바꿀지도 모릅니다.",
        },
        {
            "name": "can_do_split",
            "script": (
                "이 기술이 정말 우리의 생활을 바꿀 수 있을까요?\n"
                "로봇은 사람의 행동을 보고 복잡한 작업을 할 수\n"
                "있다고 연구진은 설명했다. BGM 전문가들은 안전 기준도 필요하다고 말했다.\n"
                "몇 년 뒤 이 기술은 너무 당연한 일상이 될지도 모릅니다."
            ),
            "first": "이 기술이 정말 우리의 생활을 바꿀 수 있을까요?",
            "last": "몇 년 뒤 이 기술은 너무 당연한 일상이 될지도 모릅니다.",
        },
        {
            "name": "short_fragments",
            "script": (
                "사람들이 이 동물의 행동에 마음을 빼앗긴 이유가 있습니다.\n"
                "고래는 구조됐다.\n"
                "그리고\n"
                "바다로 돌아갔다. 장면 전환 구조대는 관리가 중요하다고 전했다.\n"
                "그 순간은 인간과 자연의 거리를 조금 좁혀줬습니다."
            ),
            "first": "사람들이 이 동물의 행동에 마음을 빼앗긴 이유가 있습니다.",
            "last": "그 순간은 인간과 자연의 거리를 조금 좁혀줬습니다.",
        },
    ]

    results = [
        {
            "name": sample["name"],
            "script": qa.polish_script(
                sample["script"],
                protected_first=sample["first"],
                protected_last=sample["last"],
            ),
        }
        for sample in samples
    ]

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
