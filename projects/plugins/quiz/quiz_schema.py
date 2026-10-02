from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


class QuizValidationError(ValueError):
    """퀴즈 데이터가 제작 규칙을 위반했을 때 발생하는 예외."""


def _clean_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise QuizValidationError(
            f"{field_name}은 문자열이어야 합니다."
        )

    cleaned = " ".join(value.strip().split())

    if not cleaned:
        raise QuizValidationError(
            f"{field_name}은 비어 있을 수 없습니다."
        )

    return cleaned


def _estimate_display_lines(
    text: str,
    max_chars_per_line: int,
) -> int:
    if max_chars_per_line <= 0:
        raise QuizValidationError(
            "max_chars_per_line은 1 이상이어야 합니다."
        )

    compact_length = len(
        "".join(text.split())
    )

    if compact_length == 0:
        return 0

    return (
        compact_length + max_chars_per_line - 1
    ) // max_chars_per_line


@dataclass(frozen=True)
class QuizQuestion:
    id: str
    category: str
    difficulty: str
    question: str
    answer: str
    question_tts: str
    answer_tts: str
    countdown_seconds: int = 3

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        max_question_chars_per_line: int,
        max_question_lines: int,
    ) -> "QuizQuestion":
        if not isinstance(data, dict):
            raise QuizValidationError(
                "각 문제는 JSON 객체여야 합니다."
            )

        question_id = _clean_text(
            data.get("id"),
            "question.id",
        )
        category = _clean_text(
            data.get("category"),
            f"{question_id}.category",
        )
        difficulty = _clean_text(
            data.get("difficulty"),
            f"{question_id}.difficulty",
        )
        question = _clean_text(
            data.get("question"),
            f"{question_id}.question",
        )
        answer = _clean_text(
            data.get("answer"),
            f"{question_id}.answer",
        )

        question_tts = _clean_text(
            data.get("question_tts", question),
            f"{question_id}.question_tts",
        )
        answer_tts = _clean_text(
            data.get(
                "answer_tts",
                f"정답은 {answer}입니다.",
            ),
            f"{question_id}.answer_tts",
        )

        countdown_seconds = data.get(
            "countdown_seconds",
            3,
        )

        if not isinstance(countdown_seconds, int):
            raise QuizValidationError(
                f"{question_id}.countdown_seconds는 "
                "정수여야 합니다."
            )

        if countdown_seconds != 3:
            raise QuizValidationError(
                f"{question_id}: 카운트다운은 "
                "3초로 고정해야 합니다."
            )

        line_count = _estimate_display_lines(
            question,
            max_question_chars_per_line,
        )

        if line_count > max_question_lines:
            raise QuizValidationError(
                f"{question_id}: 질문이 화면 기준 "
                f"{max_question_lines}줄을 초과합니다. "
                f"현재 예상 줄 수: {line_count}, "
                f"질문: {question}"
            )

        if question == answer:
            raise QuizValidationError(
                f"{question_id}: 질문과 정답이 "
                "동일할 수 없습니다."
            )

        if len(answer) > 30:
            raise QuizValidationError(
                f"{question_id}: 정답은 화면 표시를 위해 "
                "30자 이하여야 합니다."
            )

        return cls(
            id=question_id,
            category=category,
            difficulty=difficulty,
            question=question,
            answer=answer,
            question_tts=question_tts,
            answer_tts=answer_tts,
            countdown_seconds=countdown_seconds,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuizEpisode:
    episode_id: str
    genre: str
    quiz_type: str
    title: str
    question_count: int
    questions: tuple[QuizQuestion, ...]
    ending_text: str
    ending_tts: str
    max_question_lines: int
    max_question_chars_per_line: int

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> "QuizEpisode":
        if not isinstance(data, dict):
            raise QuizValidationError(
                "퀴즈 파일 최상위 값은 "
                "JSON 객체여야 합니다."
            )

        episode_id = _clean_text(
            data.get("episode_id"),
            "episode_id",
        )
        genre = _clean_text(
            data.get("genre", "quiz"),
            "genre",
        )
        quiz_type = _clean_text(
            data.get("quiz_type", "short_answer"),
            "quiz_type",
        )
        title = _clean_text(
            data.get("title"),
            "title",
        )

        if genre != "quiz":
            raise QuizValidationError(
                "genre는 quiz여야 합니다."
            )

        if quiz_type != "short_answer":
            raise QuizValidationError(
                "quiz_type은 short_answer여야 합니다."
            )

        settings = data.get("settings", {})

        if not isinstance(settings, dict):
            raise QuizValidationError(
                "settings는 JSON 객체여야 합니다."
            )

        max_question_lines = settings.get(
            "max_question_lines",
            2,
        )
        max_question_chars_per_line = settings.get(
            "max_question_chars_per_line",
            15,
        )

        if (
            not isinstance(max_question_lines, int)
            or max_question_lines <= 0
        ):
            raise QuizValidationError(
                "max_question_lines는 "
                "1 이상의 정수여야 합니다."
            )

        if (
            not isinstance(
                max_question_chars_per_line,
                int,
            )
            or max_question_chars_per_line <= 0
        ):
            raise QuizValidationError(
                "max_question_chars_per_line은 "
                "1 이상의 정수여야 합니다."
            )

        raw_questions = data.get("questions")

        if not isinstance(raw_questions, list):
            raise QuizValidationError(
                "questions는 배열이어야 합니다."
            )

        if not raw_questions:
            raise QuizValidationError(
                "문제가 한 개 이상 필요합니다."
            )

        questions = tuple(
            QuizQuestion.from_dict(
                item,
                max_question_chars_per_line=(
                    max_question_chars_per_line
                ),
                max_question_lines=max_question_lines,
            )
            for item in raw_questions
        )

        question_ids = [
            question.id
            for question in questions
        ]

        if len(question_ids) != len(set(question_ids)):
            raise QuizValidationError(
                "문제 ID가 중복되었습니다."
            )

        question_texts = [
            question.question
            for question in questions
        ]

        if len(question_texts) != len(
            set(question_texts)
        ):
            raise QuizValidationError(
                "동일한 문제가 중복되었습니다."
            )

        ending = data.get("ending", {})

        if not isinstance(ending, dict):
            raise QuizValidationError(
                "ending은 JSON 객체여야 합니다."
            )

        ending_text = _clean_text(
            ending.get(
                "text",
                "몇 문제를 맞혔나요?",
            ),
            "ending.text",
        )
        ending_tts = _clean_text(
            ending.get(
                "tts",
                "몇 문제를 맞혔는지 "
                "댓글로 남겨주세요.",
            ),
            "ending.tts",
        )

        return cls(
            episode_id=episode_id,
            genre=genre,
            quiz_type=quiz_type,
            title=title,
            question_count=len(questions),
            questions=questions,
            ending_text=ending_text,
            ending_tts=ending_tts,
            max_question_lines=max_question_lines,
            max_question_chars_per_line=(
                max_question_chars_per_line
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "genre": self.genre,
            "quiz_type": self.quiz_type,
            "title": self.title,
            "question_count": self.question_count,
            "settings": {
                "max_question_lines": (
                    self.max_question_lines
                ),
                "max_question_chars_per_line": (
                    self.max_question_chars_per_line
                ),
                "countdown_seconds": 3,
                "question_tts_enabled": True,
                "answer_tts_enabled": True,
                "countdown_tts_enabled": False,
                "explanation_enabled": False,
            },
            "questions": [
                question.to_dict()
                for question in self.questions
            ],
            "ending": {
                "text": self.ending_text,
                "tts": self.ending_tts,
            },
        }