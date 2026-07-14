from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class DifficultyClassificationError(ValueError):
    """Question Pool 난이도 분류 입력 또는 결과가 올바르지 않을 때 발생합니다."""


_ALLOWED_LEVELS = ("elementary", "middle", "high", "current")
_SENTENCE_SPLIT_PATTERN = re.compile(r"[.!?。！？]+")
_WORD_PATTERN = re.compile(r"[0-9A-Za-z가-힣]+")
_NUMBER_PATTERN = re.compile(r"\d+(?:[.,]\d+)?")
_ACADEMIC_TERMS = {
    "가속도", "관성", "유전자", "염색체", "광합성", "세포", "분자", "원자",
    "확률", "함수", "방정식", "경제성장률", "인플레이션", "헌법", "민주주의",
    "산화", "환원", "전자", "중력", "생태계", "기후", "지질", "문명",
}
_ADVANCED_TERMS = {
    "상대성이론", "양자", "엔트로피", "미분", "적분", "로그", "복소수",
    "유전공학", "면역반응", "거시경제", "통화정책", "국제법", "열역학",
    "전자기파", "판구조론", "광전효과", "대수적", "확률분포", "표준편차",
}
_CURRENT_TERMS = {
    "오늘", "이번", "최근", "현재", "올해", "지난달", "이번달", "발표",
    "선거", "정상회담", "금리", "환율", "태풍", "속보", "정부", "국회",
    "대통령", "총선", "대회", "우승", "신제품", "출시", "수상",
}


def _clean_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise DifficultyClassificationError(f"{field_name}은 문자열이어야 합니다.")

    cleaned = " ".join(value.strip().split())

    if not cleaned:
        raise DifficultyClassificationError(f"{field_name}은 비어 있을 수 없습니다.")

    return cleaned


def _load_json(path: Path) -> dict[str, Any]:
    resolved = path.resolve()

    try:
        raw: Any = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DifficultyClassificationError(
            "Question Pool을 읽지 못했습니다.\n"
            f"파일: {resolved}\n원인: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise DifficultyClassificationError("Question Pool 최상위 값은 객체여야 합니다.")

    return raw


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary = resolved.with_suffix(resolved.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(resolved)


@dataclass(frozen=True)
class DifficultyResult:
    predicted_level: str
    confidence: float
    scores: dict[str, float]
    reasons: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "predicted_level": self.predicted_level,
            "confidence": self.confidence,
            "scores": self.scores,
            "reasons": list(self.reasons),
        }


class DifficultyClassifier:
    def classify_file(
        self,
        *,
        input_path: Path,
        output_path: Path,
        minimum_confidence: float,
        enforce_declared_level: bool,
    ) -> dict[str, Any]:
        if not 0 <= minimum_confidence <= 1:
            raise DifficultyClassificationError(
                "minimum_confidence는 0~1 사이여야 합니다."
            )

        raw_pool = _load_json(input_path)
        raw_questions = raw_pool.get("questions")

        if not isinstance(raw_questions, list) or not raw_questions:
            raise DifficultyClassificationError(
                "question_pool.questions는 비어 있지 않은 배열이어야 합니다."
            )

        classified_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        classified_questions: list[dict[str, Any]] = []
        mismatch_count = 0
        low_confidence_count = 0

        for index, raw_question in enumerate(raw_questions, start=1):
            if not isinstance(raw_question, dict):
                raise DifficultyClassificationError(
                    f"questions[{index}]은 객체여야 합니다."
                )

            normalized = dict(raw_question)
            question_id = _clean_text(
                normalized.get("id"), f"questions[{index}].id"
            )
            declared_level = _clean_text(
                normalized.get("level"), f"{question_id}.level"
            ).lower()

            if declared_level not in _ALLOWED_LEVELS:
                raise DifficultyClassificationError(
                    f"{question_id}.level은 elementary, middle, high, current 중 하나여야 합니다."
                )

            result = self.classify_question(normalized)
            matches = declared_level == result.predicted_level
            accepted = result.confidence >= minimum_confidence and (
                matches or not enforce_declared_level
            )

            if not matches:
                mismatch_count += 1

            if result.confidence < minimum_confidence:
                low_confidence_count += 1

            normalized["difficulty"] = {
                **result.to_dict(),
                "declared_level": declared_level,
                "matches_declared_level": matches,
                "accepted": accepted,
                "classified_at": classified_at,
            }
            classified_questions.append(normalized)

        output_payload = dict(raw_pool)
        output_payload["version"] = "1.2"
        output_payload["classified_at"] = classified_at
        output_payload["minimum_confidence"] = minimum_confidence
        output_payload["enforce_declared_level"] = enforce_declared_level
        output_payload["question_count"] = len(classified_questions)
        output_payload["questions"] = classified_questions
        _save_json(output_path, output_payload)

        return {
            "input_count": len(raw_questions),
            "classified_count": len(classified_questions),
            "mismatch_count": mismatch_count,
            "low_confidence_count": low_confidence_count,
            "output": str(output_path.resolve()),
        }

    def classify_question(self, question: dict[str, Any]) -> DifficultyResult:
        prompt = _clean_text(question.get("question"), "question.question")
        answer = _clean_text(question.get("answer"), "question.answer")
        explanation = _clean_text(
            question.get("explanation"), "question.explanation"
        )
        category = _clean_text(question.get("category"), "question.category").lower()
        published_at = question.get("published_at")
        evergreen = bool(question.get("evergreen", True))

        combined = f"{prompt} {answer} {explanation}".lower()
        words = _WORD_PATTERN.findall(combined)
        sentence_count = max(
            1,
            len([part for part in _SENTENCE_SPLIT_PATTERN.split(combined) if part]),
        )
        average_word_length = (
            sum(len(word) for word in words) / len(words) if words else 0.0
        )
        academic_count = sum(1 for term in _ACADEMIC_TERMS if term in combined)
        advanced_count = sum(1 for term in _ADVANCED_TERMS if term in combined)
        current_count = sum(1 for term in _CURRENT_TERMS if term in combined)
        number_count = len(_NUMBER_PATTERN.findall(combined))
        total_length = len(prompt) + len(answer) + len(explanation)

        scores = {
            "elementary": 35.0,
            "middle": 25.0,
            "high": 15.0,
            "current": 5.0,
        }
        reasons: list[str] = []

        if category in {"current", "society", "economy", "politics", "news"}:
            scores["current"] += 35
            reasons.append("시사·사회 계열 카테고리")

        if published_at is not None or not evergreen:
            scores["current"] += 35
            reasons.append("발행일 또는 비상시성 정보 존재")

        if current_count:
            scores["current"] += min(30.0, current_count * 8.0)
            reasons.append("최근성 표현 포함")

        if total_length <= 70 and average_word_length <= 3.2:
            scores["elementary"] += 24
            reasons.append("짧고 단순한 문장")
        elif total_length <= 140:
            scores["middle"] += 24
            reasons.append("중간 길이의 설명")
        else:
            scores["high"] += 24
            reasons.append("긴 설명과 높은 정보 밀도")

        if academic_count:
            scores["middle"] += min(24.0, academic_count * 7.0)
            scores["high"] += min(14.0, academic_count * 4.0)
            reasons.append("교과 개념어 포함")

        if advanced_count:
            scores["high"] += min(45.0, advanced_count * 15.0)
            reasons.append("고급 개념어 포함")

        if number_count >= 2:
            scores["middle"] += 6
            scores["high"] += 8
            reasons.append("수치 정보 다수 포함")

        if sentence_count >= 3:
            scores["high"] += 8

        if len(answer) <= 12:
            scores["elementary"] += 7
        elif len(answer) >= 25:
            scores["high"] += 7

        normalized_scores = self._softmax(scores)
        predicted_level = max(normalized_scores, key=normalized_scores.get)
        confidence = round(normalized_scores[predicted_level], 4)

        if not reasons:
            reasons.append("기본 문장 복잡도 기준")

        return DifficultyResult(
            predicted_level=predicted_level,
            confidence=confidence,
            scores={
                level: round(normalized_scores[level], 4)
                for level in _ALLOWED_LEVELS
            },
            reasons=tuple(dict.fromkeys(reasons)),
        )

    @staticmethod
    def _softmax(scores: dict[str, float]) -> dict[str, float]:
        maximum = max(scores.values())
        exponents = {
            key: math.exp((value - maximum) / 12.0)
            for key, value in scores.items()
        }
        total = sum(exponents.values())
        return {key: value / total for key, value in exponents.items()}
