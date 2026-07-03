from __future__ import annotations

import logging

from app.research.research_types import ResearchContext, ResearchInput
from app.research.source_planner import SourcePlanner
from app.research.topic_extractor import TopicExtractor


logger = logging.getLogger(__name__)


class ResearchContextBuilder:
    def __init__(self) -> None:
        self.topic_extractor = TopicExtractor()
        self.source_planner = SourcePlanner()

    def build(
        self,
        title: str,
        summary: str = "",
        source: str = "",
        url: str = "",
    ) -> dict[str, object]:
        item = ResearchInput(
            title=title,
            summary=summary,
            source=source,
            url=url,
        )
        topic = self.topic_extractor.extract(item)
        context = self._build_rule_based_context(item, topic)
        logger.info("Research context built for topic=%s", topic)
        return context.to_dict()

    def _build_rule_based_context(
        self,
        item: ResearchInput,
        topic: str,
    ) -> ResearchContext:
        lowered = item.combined_text().lower()
        source_plan = self.source_planner.plan(topic)

        if any(keyword in lowered for keyword in ["webb", "nasa", "space", "telescope", "우주", "망원경"]):
            return ResearchContext(
                topic=topic,
                core_question="이 관측은 왜 단순한 사진이나 발견을 넘어 중요한 단서가 되는가?",
                background_points=[
                    "우주망원경 관측은 지상 관측으로 보기 어려운 희미한 신호를 포착하는 데 강점이 있습니다.",
                    "새로운 신호는 천체의 형성 과정이나 대기 성분을 추정하는 단서가 될 수 있습니다.",
                    "공식 발표와 후속 관측이 함께 확인되어야 의미가 분명해집니다.",
                ],
                related_angles=[
                    "과거에도 하나의 희미한 신호가 행성이나 별의 이해를 바꾼 사례가 있습니다.",
                    "관측 장비의 성능이 좋아질수록 처음에는 설명하기 어려운 데이터가 더 많이 드러납니다.",
                    "대중이 흥미를 느끼는 지점은 발견 자체보다 아직 풀리지 않은 질문입니다.",
                ],
                story_clues=[
                    "첫 단서는 작고 흐릿한 신호입니다.",
                    "이상한 점은 신호의 정체가 바로 설명되지 않는다는 것입니다.",
                    "현재까지 밝혀진 것은 관측 사실이고, 남은 의문은 그 의미입니다.",
                ],
                possible_resolution="후속 관측이 같은 신호를 다시 확인하면, 이 발견은 새로운 우주 해석의 출발점이 될 수 있습니다.",
                source_plan=source_plan,
            )

        if any(keyword in lowered for keyword in ["ai", "robot", "technology", "로봇", "인공지능", "기술"]):
            return ResearchContext(
                topic=topic,
                core_question="이 기술은 왜 단순한 시연이 아니라 일상 변화의 신호인가?",
                background_points=[
                    "로봇 기술의 핵심은 정해진 명령을 넘어 새로운 상황에 적응하는 능력입니다.",
                    "사람의 행동을 보고 배우는 방식은 제조, 돌봄, 물류 현장과 연결됩니다.",
                    "기술 확산에는 안전 기준과 책임 문제가 함께 따라옵니다.",
                ],
                related_angles=[
                    "과거 자동화 기술도 처음에는 실험실 장면으로 보였지만 빠르게 현장으로 들어왔습니다.",
                    "인공지능 로봇은 편리함과 불안감을 동시에 만드는 주제입니다.",
                    "핵심 쟁점은 무엇을 할 수 있느냐보다 어디까지 맡길 수 있느냐입니다.",
                ],
                story_clues=[
                    "첫 장면은 로봇이 사람의 행동을 지켜보는 순간입니다.",
                    "긴장감은 그 행동을 스스로 따라 하기 시작할 때 생깁니다.",
                    "남은 질문은 이 기술을 어떤 기준으로 사용할지입니다.",
                ],
                possible_resolution="기술의 가능성은 커지고 있지만, 실제 변화는 안전성과 신뢰가 확보될 때 시작됩니다.",
                source_plan=source_plan,
            )

        if any(keyword in lowered for keyword in ["whale", "animal", "rescue", "고래", "동물", "구조"]):
            return ResearchContext(
                topic=topic,
                core_question="이 구조 장면은 왜 한 동물의 생존을 넘어 더 큰 메시지가 되는가?",
                background_points=[
                    "해양 동물 구조는 현장의 빠른 판단과 시민 협력이 함께 필요합니다.",
                    "그물과 해양 쓰레기는 반복적으로 동물에게 위험을 만듭니다.",
                    "구조 이후에도 같은 사고를 줄이는 관리가 중요합니다.",
                ],
                related_angles=[
                    "과거에도 해안가 구조 사례는 해양 보호 논의로 이어졌습니다.",
                    "사람들이 감동하는 이유는 생명이 다시 자연으로 돌아가는 장면 때문입니다.",
                    "개별 사건은 해양 환경 문제를 설명하는 강한 이야기 소재가 됩니다.",
                ],
                story_clues=[
                    "시작은 그물에 걸린 고래의 위기입니다.",
                    "전환점은 구조대와 시민들이 같은 목표로 움직이는 순간입니다.",
                    "남은 질문은 이런 사고를 어떻게 줄일 수 있느냐입니다.",
                ],
                possible_resolution="이 이야기는 구조 성공으로 끝나지만, 진짜 결말은 바다를 더 안전하게 만드는 변화에 달려 있습니다.",
                source_plan=source_plan,
            )

        return ResearchContext(
            topic=topic,
            core_question="왜 이 뉴스가 지금 사람들의 관심을 받을 만한가?",
            background_points=[
                "사건의 표면적인 결과보다 그 배경을 함께 봐야 의미가 분명해집니다.",
                "관련 사례를 비교하면 이번 일이 일회성인지 흐름의 일부인지 알 수 있습니다.",
                "공식 자료와 후속 보도를 함께 확인해야 과장을 줄일 수 있습니다.",
            ],
            related_angles=[
                "시청자가 궁금해할 지점은 왜 지금 이 일이 벌어졌는가입니다.",
                "비슷한 사례와 연결하면 단순 뉴스가 하나의 이야기로 바뀝니다.",
                "남은 의문을 분명히 제시하면 결말에 여운이 생깁니다.",
            ],
            story_clues=[
                "첫 단서는 기사 제목에 드러난 변화입니다.",
                "이상한 점은 아직 설명되지 않은 배경입니다.",
                "현재까지 확인된 사실과 남은 질문을 나눠 보여줘야 합니다.",
            ],
            possible_resolution="추가 자료가 확인될수록 이 사건의 의미는 더 선명해질 수 있습니다.",
            source_plan=source_plan,
        )
