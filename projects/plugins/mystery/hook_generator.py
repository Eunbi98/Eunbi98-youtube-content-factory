from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class HookCandidate:
    text: str
    score: float
    reasons: list[str]


class HookGenerator:
    def generate(self, *, topic: str) -> list[HookCandidate]:
        topic = " ".join(topic.strip().split())
        if not topic:
            raise ValueError("topic은 비어 있을 수 없습니다.")

        templates = [
            f"{topic}, 정말 사실일까요?",
            f"{topic}에는 무엇이 숨겨져 있을까요?",
            f"{topic}, 우리가 잘못 알고 있던 걸까요?",
            f"{topic}의 진실은 따로 있을까요?",
            f"{topic}, 아직도 풀리지 않은 이유는?",
            f"{topic}에서 실제로 무슨 일이 있었을까요?",
            f"{topic}, 기록은 무엇을 말할까요?",
            f"{topic}은 미스터리일까요, 오해일까요?",
        ]

        return sorted(
            [self._score(text) for text in templates],
            key=lambda item: item.score,
            reverse=True,
        )

    def best(self, *, topic: str) -> HookCandidate:
        return self.generate(topic=topic)[0]

    def _score(self, text: str) -> HookCandidate:
        score = 0.0
        reasons: list[str] = []

        if text.endswith("?"):
            score += 35.0
            reasons.append("question")
        if len(text) <= 24:
            score += 25.0
            reasons.append("short")
        if any(word in text for word in ("진실", "숨겨", "풀리지", "실제로", "잘못", "미스터리")):
            score += 25.0
            reasons.append("curiosity")
        if "정말" in text:
            score += 10.0
            reasons.append("certainty_challenge")
        if "무엇" in text or "왜" in text:
            score += 5.0
            reasons.append("open_loop")

        return HookCandidate(
            text=text,
            score=round(min(score, 100.0), 1),
            reasons=reasons,
        )
