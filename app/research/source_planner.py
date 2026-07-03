from __future__ import annotations

from app.research.research_types import SourcePlanItem


class SourcePlanner:
    def plan(self, topic: str) -> list[SourcePlanItem]:
        common_plan = [
            SourcePlanItem(
                source_type="공식자료",
                purpose="사건의 원문 발표와 확인된 사실 확인",
                query_hint=f"{topic} 공식 발표 원문",
                priority=1,
            ),
            SourcePlanItem(
                source_type="관련 보도",
                purpose="다른 매체가 주목한 쟁점 비교",
                query_hint=f"{topic} 관련 보도 분석",
                priority=2,
            ),
            SourcePlanItem(
                source_type="배경 지식",
                purpose="시청자가 이해해야 할 기본 개념 정리",
                query_hint=f"{topic} 배경 지식",
                priority=2,
            ),
            SourcePlanItem(
                source_type="과거 유사 사례",
                purpose="이번 일이 처음인지, 반복되는 흐름인지 확인",
                query_hint=f"{topic} 과거 유사 사례",
                priority=3,
            ),
            SourcePlanItem(
                source_type="후속 연구 가능성",
                purpose="앞으로 무엇이 확인되어야 하는지 정리",
                query_hint=f"{topic} 후속 연구 가능성",
                priority=3,
            ),
            SourcePlanItem(
                source_type="위키/백과 참고",
                purpose="핵심 용어와 인물, 기관의 기본 정보 확인",
                query_hint=f"{topic} 백과 사전",
                priority=4,
            ),
            SourcePlanItem(
                source_type="영상 자료 참고",
                purpose="쇼츠 시각 자료와 장면 구성 아이디어 확보",
                query_hint=f"{topic} 영상 자료",
                priority=4,
            ),
        ]

        return common_plan
