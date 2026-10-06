from __future__ import annotations

import hashlib
import json
import random
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable


class QuestionEngineError(ValueError):
    """Question Engine 처리 중 발생하는 오류."""


ALLOWED_CATEGORIES = {
    "science",
    "history",
    "geography",
    "language",
    "society",
    "culture",
    "news",
    "general",
}

ALLOWED_DIFFICULTIES = {
    "easy",
    "normal",
    "hard",
}

DIFFICULTY_WEIGHT = {
    "easy": 1,
    "normal": 2,
    "hard": 3,
}


def clean_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise QuestionEngineError(
            f"{field_name}은 문자열이어야 합니다."
        )

    cleaned = " ".join(value.strip().split())

    if not cleaned:
        raise QuestionEngineError(
            f"{field_name}은 비어 있을 수 없습니다."
        )

    return cleaned


def normalize_question_text(text: str) -> str:
    normalized = text.lower()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = re.sub(
        r"[?？!！.,·:;\"'“”‘’()\[\]{}<>]",
        "",
        normalized,
    )
    return normalized


def estimate_display_lines(
    text: str,
    chars_per_line: int,
) -> int:
    compact_length = len(
        re.sub(r"\s+", "", text)
    )

    if compact_length == 0:
        return 0

    return (
        compact_length
        + chars_per_line
        - 1
    ) // chars_per_line


def make_question_hash(
    question: str,
    answer: str,
) -> str:
    raw = (
        normalize_question_text(question)
        + "::"
        + normalize_question_text(answer)
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class QuestionCandidate:
    id: str
    category: str
    difficulty: str
    question: str
    answer: str
    question_tts: str
    answer_tts: str
    source_type: str
    source_name: str
    verified_at: str | None
    evergreen: bool
    priority: int
    tags: tuple[str, ...]
    quality_score: float
    question_hash: str

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
        *,
        max_question_lines: int,
        max_chars_per_line: int,
    ) -> "QuestionCandidate":
        if not isinstance(data, dict):
            raise QuestionEngineError(
                "Question Bank의 각 문제는 "
                "JSON 객체여야 합니다."
            )

        question_id = clean_text(
            data.get("id"),
            "question.id",
        )
        category = clean_text(
            data.get("category", "general"),
            f"{question_id}.category",
        ).lower()
        difficulty = clean_text(
            data.get("difficulty", "normal"),
            f"{question_id}.difficulty",
        ).lower()
        question = clean_text(
            data.get("question"),
            f"{question_id}.question",
        )
        answer = clean_text(
            data.get("answer"),
            f"{question_id}.answer",
        )
        question_tts = clean_text(
            data.get("question_tts", question),
            f"{question_id}.question_tts",
        )
        answer_tts = clean_text(
            data.get(
                "answer_tts",
                f"정답은 {answer}입니다.",
            ),
            f"{question_id}.answer_tts",
        )
        source_type = clean_text(
            data.get("source_type", "internal"),
            f"{question_id}.source_type",
        )
        source_name = clean_text(
            data.get("source_name", "question_bank"),
            f"{question_id}.source_name",
        )

        if category not in ALLOWED_CATEGORIES:
            raise QuestionEngineError(
                f"{question_id}: 지원하지 않는 "
                f"category입니다: {category}"
            )

        if difficulty not in ALLOWED_DIFFICULTIES:
            raise QuestionEngineError(
                f"{question_id}: 지원하지 않는 "
                f"difficulty입니다: {difficulty}"
            )

        evergreen = data.get(
            "evergreen",
            True,
        )

        if not isinstance(evergreen, bool):
            raise QuestionEngineError(
                f"{question_id}.evergreen은 "
                "boolean이어야 합니다."
            )

        priority = data.get(
            "priority",
            50,
        )

        if (
            not isinstance(priority, int)
            or isinstance(priority, bool)
            or not 0 <= priority <= 100
        ):
            raise QuestionEngineError(
                f"{question_id}.priority는 "
                "0~100의 정수여야 합니다."
            )

        verified_at_value = data.get(
            "verified_at"
        )

        if verified_at_value is None:
            verified_at = None
        else:
            verified_at = clean_text(
                verified_at_value,
                f"{question_id}.verified_at",
            )

        raw_tags = data.get("tags", [])

        if not isinstance(raw_tags, list):
            raise QuestionEngineError(
                f"{question_id}.tags는 "
                "배열이어야 합니다."
            )

        tags = tuple(
            clean_text(
                tag,
                f"{question_id}.tags",
            ).lower()
            for tag in raw_tags
        )

        line_count = estimate_display_lines(
            question,
            max_chars_per_line,
        )

        if line_count > max_question_lines:
            raise QuestionEngineError(
                f"{question_id}: 질문이 화면 기준 "
                f"{max_question_lines}줄을 초과합니다. "
                f"예상 줄 수: {line_count}, "
                f"질문: {question}"
            )

        if len(answer) > 30:
            raise QuestionEngineError(
                f"{question_id}: 정답은 "
                "30자 이하여야 합니다."
            )

        quality_score = (
            cls.calculate_quality_score(
                question=question,
                answer=answer,
                question_tts=question_tts,
                answer_tts=answer_tts,
                evergreen=evergreen,
                verified_at=verified_at,
                priority=priority,
            )
        )

        return cls(
            id=question_id,
            category=category,
            difficulty=difficulty,
            question=question,
            answer=answer,
            question_tts=question_tts,
            answer_tts=answer_tts,
            source_type=source_type,
            source_name=source_name,
            verified_at=verified_at,
            evergreen=evergreen,
            priority=priority,
            tags=tags,
            quality_score=quality_score,
            question_hash=make_question_hash(
                question,
                answer,
            ),
        )

    @staticmethod
    def calculate_quality_score(
        *,
        question: str,
        answer: str,
        question_tts: str,
        answer_tts: str,
        evergreen: bool,
        verified_at: str | None,
        priority: int,
    ) -> float:
        score = 50.0

        compact_question_length = len(
            re.sub(r"\s+", "", question)
        )

        if 8 <= compact_question_length <= 26:
            score += 15.0
        elif compact_question_length <= 30:
            score += 8.0

        if 1 <= len(answer) <= 12:
            score += 10.0
        elif len(answer) <= 20:
            score += 5.0

        if question_tts != question:
            score += 5.0

        if answer_tts.startswith("정답은"):
            score += 5.0

        if evergreen:
            score += 5.0

        if verified_at:
            score += 5.0

        score += priority * 0.05

        return round(
            min(score, 100.0),
            2,
        )

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["tags"] = list(self.tags)
        return result


@dataclass(frozen=True)
class QuestionSelectionResult:
    episode_id: str
    title: str
    requested_count: int
    selected_count: int
    seed: int
    selected_questions: tuple[
        QuestionCandidate,
        ...
    ]
    rejected_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "title": self.title,
            "requested_count": (
                self.requested_count
            ),
            "selected_count": (
                self.selected_count
            ),
            "seed": self.seed,
            "selected_questions": [
                question.to_dict()
                for question
                in self.selected_questions
            ],
            "rejected_ids": list(
                self.rejected_ids
            ),
        }

    def to_quiz_input_dict(
        self,
    ) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "genre": "quiz",
            "quiz_type": "short_answer",
            "title": self.title,
            "settings": {
                "max_question_lines": 2,
                "max_question_chars_per_line": 15,
            },
            "questions": [
                {
                    "id": f"q{index:03d}",
                    "source_question_id": (
                        question.id
                    ),
                    "category": (
                        question.category
                    ),
                    "difficulty": (
                        question.difficulty
                    ),
                    "question": (
                        question.question
                    ),
                    "answer": question.answer,
                    "question_tts": (
                        question.question_tts
                    ),
                    "answer_tts": (
                        question.answer_tts
                    ),
                    "countdown_seconds": 3,
                }
                for index, question in enumerate(
                    self.selected_questions,
                    start=1,
                )
            ],
            "ending": {
                "text": "몇 문제를 맞혔나요?",
                "tts": (
                    "몇 문제를 맞혔는지 "
                    "댓글로 남겨주세요."
                ),
            },
        }


class QuestionBank:
    def __init__(
        self,
        *,
        max_question_lines: int = 2,
        max_chars_per_line: int = 15,
    ) -> None:
        self.max_question_lines = (
            max_question_lines
        )
        self.max_chars_per_line = (
            max_chars_per_line
        )

    def load_directory(
        self,
        bank_dir: Path,
    ) -> tuple[QuestionCandidate, ...]:
        resolved_dir = bank_dir.resolve()

        if not resolved_dir.exists():
            raise FileNotFoundError(
                f"Question Bank 폴더가 없습니다: "
                f"{resolved_dir}"
            )

        if not resolved_dir.is_dir():
            raise QuestionEngineError(
                f"Question Bank 경로가 "
                f"폴더가 아닙니다: {resolved_dir}"
            )

        json_paths = sorted(
            resolved_dir.glob("*.json")
        )

        if not json_paths:
            raise QuestionEngineError(
                "Question Bank JSON 파일이 "
                "없습니다."
            )

        candidates: list[
            QuestionCandidate
        ] = []

        for json_path in json_paths:
            candidates.extend(
                self.load_file(json_path)
            )

        self.validate_unique_ids(
            candidates
        )

        return tuple(candidates)

    def load_file(
        self,
        path: Path,
    ) -> tuple[QuestionCandidate, ...]:
        try:
            with path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise QuestionEngineError(
                f"Question Bank JSON 오류: "
                f"{path}\n{error}"
            ) from error

        if isinstance(data, dict):
            raw_questions = data.get(
                "questions"
            )
        else:
            raw_questions = data

        if not isinstance(
            raw_questions,
            list,
        ):
            raise QuestionEngineError(
                f"{path}: questions 배열이 "
                "필요합니다."
            )

        return tuple(
            QuestionCandidate.from_dict(
                item,
                max_question_lines=(
                    self.max_question_lines
                ),
                max_chars_per_line=(
                    self.max_chars_per_line
                ),
            )
            for item in raw_questions
        )

    @staticmethod
    def validate_unique_ids(
        candidates: Iterable[
            QuestionCandidate
        ],
    ) -> None:
        seen_ids: set[str] = set()

        for candidate in candidates:
            if candidate.id in seen_ids:
                raise QuestionEngineError(
                    "Question Bank 문제 ID가 "
                    f"중복되었습니다: {candidate.id}"
                )

            seen_ids.add(candidate.id)


class QuestionEngine:
    def __init__(
        self,
        *,
        minimum_quality_score: float = 75.0,
    ) -> None:
        self.minimum_quality_score = (
            minimum_quality_score
        )

    def select(
        self,
        *,
        episode_id: str,
        title: str,
        candidates: Iterable[
            QuestionCandidate
        ],
        count: int,
        seed: int,
        categories: set[str] | None = None,
        excluded_hashes: set[str] | None = None,
    ) -> QuestionSelectionResult:
        if count <= 0:
            raise QuestionEngineError(
                "선택 문제 수는 "
                "1개 이상이어야 합니다."
            )

        category_filter = (
            categories
            if categories
            else set(ALLOWED_CATEGORIES)
        )

        invalid_categories = (
            category_filter
            - ALLOWED_CATEGORIES
        )

        if invalid_categories:
            raise QuestionEngineError(
                "지원하지 않는 카테고리: "
                + ", ".join(
                    sorted(invalid_categories)
                )
            )

        excluded = excluded_hashes or set()

        filtered: list[
            QuestionCandidate
        ] = []
        rejected_ids: list[str] = []
        seen_hashes: set[str] = set()

        for candidate in candidates:
            if (
                candidate.category
                not in category_filter
            ):
                rejected_ids.append(
                    candidate.id
                )
                continue

            if (
                candidate.quality_score
                < self.minimum_quality_score
            ):
                rejected_ids.append(
                    candidate.id
                )
                continue

            if (
                candidate.question_hash
                in excluded
            ):
                rejected_ids.append(
                    candidate.id
                )
                continue

            if (
                candidate.question_hash
                in seen_hashes
            ):
                rejected_ids.append(
                    candidate.id
                )
                continue

            seen_hashes.add(
                candidate.question_hash
            )
            filtered.append(candidate)

        if len(filtered) < count:
            raise QuestionEngineError(
                "조건을 통과한 문제가 부족합니다. "
                f"필요: {count}, "
                f"사용 가능: {len(filtered)}"
            )

        randomizer = random.Random(seed)

        ranked = sorted(
            filtered,
            key=lambda item: (
                -item.quality_score,
                -item.priority,
                DIFFICULTY_WEIGHT[
                    item.difficulty
                ],
                randomizer.random(),
            ),
        )

        selected = self._select_balanced(
            ranked=ranked,
            count=count,
        )

        return QuestionSelectionResult(
            episode_id=episode_id,
            title=title,
            requested_count=count,
            selected_count=len(selected),
            seed=seed,
            selected_questions=tuple(
                selected
            ),
            rejected_ids=tuple(
                rejected_ids
            ),
        )

    def _select_balanced(
        self,
        *,
        ranked: list[QuestionCandidate],
        count: int,
    ) -> list[QuestionCandidate]:
        selected: list[
            QuestionCandidate
        ] = []
        selected_ids: set[str] = set()
        category_counts: dict[str, int] = {}
        difficulty_counts: dict[str, int] = {}

        desired_difficulties = (
            self._difficulty_plan(count)
        )

        for desired_difficulty in (
            desired_difficulties
        ):
            candidate = self._find_best_candidate(
                ranked=ranked,
                selected_ids=selected_ids,
                desired_difficulty=(
                    desired_difficulty
                ),
                category_counts=(
                    category_counts
                ),
            )

            if candidate is None:
                continue

            selected.append(candidate)
            selected_ids.add(candidate.id)

            category_counts[
                candidate.category
            ] = (
                category_counts.get(
                    candidate.category,
                    0,
                )
                + 1
            )

            difficulty_counts[
                candidate.difficulty
            ] = (
                difficulty_counts.get(
                    candidate.difficulty,
                    0,
                )
                + 1
            )

        if len(selected) < count:
            for candidate in ranked:
                if candidate.id in selected_ids:
                    continue

                selected.append(candidate)
                selected_ids.add(candidate.id)

                if len(selected) == count:
                    break

        selected.sort(
            key=lambda item: (
                DIFFICULTY_WEIGHT[
                    item.difficulty
                ],
                -item.quality_score,
            )
        )

        return selected[:count]

    @staticmethod
    def _difficulty_plan(
        count: int,
    ) -> list[str]:
        if count == 1:
            return ["normal"]

        if count == 2:
            return ["easy", "normal"]

        if count == 3:
            return [
                "easy",
                "normal",
                "hard",
            ]

        if count == 4:
            return [
                "easy",
                "easy",
                "normal",
                "hard",
            ]

        plan = [
            "easy",
            "easy",
            "normal",
            "normal",
            "hard",
        ]

        while len(plan) < count:
            plan.append("normal")

        return plan[:count]

    @staticmethod
    def _find_best_candidate(
        *,
        ranked: list[QuestionCandidate],
        selected_ids: set[str],
        desired_difficulty: str,
        category_counts: dict[str, int],
    ) -> QuestionCandidate | None:
        matching = [
            candidate
            for candidate in ranked
            if (
                candidate.id
                not in selected_ids
                and candidate.difficulty
                == desired_difficulty
            )
        ]

        if not matching:
            return None

        return min(
            matching,
            key=lambda item: (
                category_counts.get(
                    item.category,
                    0,
                ),
                -item.quality_score,
                -item.priority,
            ),
        )


def load_excluded_hashes(
    history_paths: Iterable[Path],
) -> set[str]:
    excluded: set[str] = set()

    for history_path in history_paths:
        if not history_path.exists():
            continue

        try:
            with history_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except (
            json.JSONDecodeError,
            OSError,
        ):
            continue

        if not isinstance(data, dict):
            continue

        raw_questions = data.get(
            "selected_questions",
            [],
        )

        if not isinstance(raw_questions, list):
            continue

        for item in raw_questions:
            if not isinstance(item, dict):
                continue

            question_hash = item.get(
                "question_hash"
            )

            if isinstance(
                question_hash,
                str,
            ):
                excluded.add(question_hash)

    return excluded