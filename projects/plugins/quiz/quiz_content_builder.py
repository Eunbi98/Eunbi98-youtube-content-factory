from __future__ import annotations

import json
import random
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class QuizContentBuildError(ValueError):
    """Question Pool에서 퀴즈 에피소드 입력을 만들 수 없을 때 발생합니다."""


_ALLOWED_LEVELS = {"elementary", "middle", "high", "current"}
_NON_WORD_PATTERN = re.compile(r"[^0-9A-Za-z가-힣]+")


def _clean_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise QuizContentBuildError(f"{field_name}은 문자열이어야 합니다.")

    cleaned = " ".join(value.strip().split())

    if not cleaned:
        raise QuizContentBuildError(f"{field_name}은 비어 있을 수 없습니다.")

    return cleaned


def _load_json(path: Path) -> dict[str, Any]:
    resolved = path.resolve()

    try:
        raw: Any = json.loads(resolved.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuizContentBuildError(
            "Question Pool을 읽지 못했습니다.\n"
            f"파일: {resolved}\n원인: {exc}"
        ) from exc

    if not isinstance(raw, dict):
        raise QuizContentBuildError("Question Pool 최상위 값은 객체여야 합니다.")

    return raw


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    resolved = path.resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    temporary = resolved.with_suffix(resolved.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(resolved)


def _normalize_key(question: str, answer: str) -> str:
    return _NON_WORD_PATTERN.sub("", f"{question}{answer}".lower())


def _estimated_line_count(text: str, chars_per_line: int) -> int:
    compact = "".join(text.split())
    return max(1, (len(compact) + chars_per_line - 1) // chars_per_line)


@dataclass(frozen=True)
class SelectedQuestion:
    source_id: str
    category: str
    level: str
    question: str
    answer: str
    explanation: str
    quality_score: float
    source_name: str
    source_url: str


class QuizContentBuilder:
    def build(
        self,
        *,
        question_pool_paths: tuple[Path, ...],
        output_path: Path,
        episode_id: str,
        title: str,
        count: int,
        level: str,
        seed: int,
        minimum_quality: float,
        categories: set[str] | None,
        ending_text: str,
        ending_tts: str,
    ) -> dict[str, Any]:
        normalized_episode_id = self._normalize_episode_id(episode_id)
        normalized_level = level.strip().lower()

        if normalized_level not in _ALLOWED_LEVELS:
            raise QuizContentBuildError(
                "level은 elementary, middle, high, current 중 하나여야 합니다."
            )

        if count <= 0:
            raise QuizContentBuildError("count는 1 이상이어야 합니다.")

        if not 0 <= minimum_quality <= 100:
            raise QuizContentBuildError("minimum_quality는 0~100 사이여야 합니다.")

        if not question_pool_paths:
            raise QuizContentBuildError("Question Pool 경로가 없습니다.")

        raw_questions: list[dict[str, Any]] = []
        loaded_paths: list[Path] = []

        for pool_path in question_pool_paths:
            if not pool_path.exists():
                continue

            raw_pool = _load_json(pool_path)
            pool_questions = raw_pool.get("questions")

            if not isinstance(pool_questions, list):
                raise QuizContentBuildError(
                    f"Question Pool의 questions는 배열이어야 합니다: {pool_path}"
                )

            loaded_paths.append(pool_path.resolve())

            for raw_question in pool_questions:
                if isinstance(raw_question, dict):
                    raw_questions.append(raw_question)

        if not raw_questions:
            raise QuizContentBuildError(
                "읽을 수 있는 Question Pool 문제가 없습니다.\n"
                + "\n".join(str(path) for path in question_pool_paths)
            )

        candidates: list[SelectedQuestion] = []
        fallback_candidates: list[SelectedQuestion] = []
        seen: set[str] = set()

        for index, raw_question in enumerate(raw_questions, start=1):
            if not isinstance(raw_question, dict):
                raise QuizContentBuildError(f"questions[{index}]은 객체여야 합니다.")

            candidate = self._parse_candidate(raw_question, index=index)

            if candidate.level != normalized_level:
                continue

            if categories and candidate.category not in categories:
                continue

            if candidate.quality_score < minimum_quality:
                continue

            candidate = self._with_compact_question(candidate)

            if _estimated_line_count(candidate.question, 15) > 2:
                continue

            key = _normalize_key(candidate.question, candidate.answer)

            if key in seen:
                continue

            seen.add(key)

            if self._is_accepted(raw_question):
                candidates.append(candidate)
            else:
                fallback_candidates.append(candidate)

        if len(candidates) < count:
            fallback_candidates.sort(
                key=lambda item: (-item.quality_score, item.source_id)
            )
            needed = count - len(candidates)
            candidates.extend(fallback_candidates[:needed])

        if len(candidates) < count:
            raise QuizContentBuildError(
                "조건을 통과한 문제가 부족합니다. "
                f"요청: {count}개, 사용 가능: {len(candidates)}개. "
                "Fact Pool 또는 Question Pool의 문제 수를 늘려야 합니다."
            )

        rng = random.Random(seed)
        candidates.sort(
            key=lambda item: (-item.quality_score, item.source_id)
        )
        selection_window = candidates[: max(count * 3, count)]
        selected = rng.sample(selection_window, count)
        selected.sort(
            key=lambda item: (-item.quality_score, item.source_id)
        )

        questions: list[dict[str, Any]] = []

        for order, item in enumerate(selected, start=1):
            question_id = f"q{order:03d}"
            questions.append(
                {
                    "id": question_id,
                    "category": item.category,
                    "difficulty": item.level,
                    "question": item.question,
                    "answer": item.answer,
                    "question_tts": item.question,
                    "answer_tts": f"정답은 {item.answer}입니다.",
                    "countdown_seconds": 3,
                    "explanation": item.explanation,
                    "source": {
                        "question_id": item.source_id,
                        "name": item.source_name,
                        "url": item.source_url,
                    },
                }
            )

        payload: dict[str, Any] = {
            "episode_id": normalized_episode_id,
            "genre": "quiz",
            "quiz_type": "short_answer",
            "title": _clean_text(title, "title"),
            "question_count": len(questions),
            "settings": {
                "max_question_lines": 2,
                "max_question_chars_per_line": 15,
            },
            "questions": questions,
            "ending": {
                "text": _clean_text(ending_text, "ending_text"),
                "tts": _clean_text(ending_tts, "ending_tts"),
            },
            "build_metadata": {
                "version": "8.4.5",
                "built_at": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat(),
                "source_pools": [str(path) for path in loaded_paths],
                "level": normalized_level,
                "seed": seed,
                "minimum_quality": minimum_quality,
                "categories": sorted(categories) if categories else [],
            },
        }

        _write_json_atomic(output_path, payload)
        return payload


    @staticmethod
    def _with_compact_question(
        candidate: SelectedQuestion,
    ) -> SelectedQuestion:
        question = candidate.question
        prefixes = (
            "빈칸에 들어갈 말은 무엇일까요? ",
            "다음 설명에 해당하는 답은 무엇일까요? ",
        )

        for prefix in prefixes:
            if question.startswith(prefix):
                body = question[len(prefix):].strip()
                body = body.rstrip("? ")

                if "□" in body:
                    compact = f"{body} 빈칸은?"
                else:
                    compact = f"{body} 정답은?"

                if len("".join(compact.split())) <= 30:
                    question = compact
                break

        return SelectedQuestion(
            source_id=candidate.source_id,
            category=candidate.category,
            level=candidate.level,
            question=question,
            answer=candidate.answer,
            explanation=candidate.explanation,
            quality_score=candidate.quality_score,
            source_name=candidate.source_name,
            source_url=candidate.source_url,
        )

    @staticmethod
    def _normalize_episode_id(raw_value: str) -> str:
        value = raw_value.strip().lower()
        number_text = value[2:] if value.startswith("ep") else value

        if not number_text.isdigit():
            raise QuizContentBuildError(
                "episode_id 형식이 올바르지 않습니다. 예: ep011"
            )

        return f"ep{int(number_text):03d}"

    @staticmethod
    def _is_accepted(raw_question: dict[str, Any]) -> bool:
        validation = raw_question.get("validation")

        if isinstance(validation, dict) and validation.get("accepted") is False:
            return False

        difficulty = raw_question.get("difficulty")

        if isinstance(difficulty, dict) and difficulty.get("accepted") is False:
            return False

        return True

    @staticmethod
    def _parse_candidate(
        raw_question: dict[str, Any],
        *,
        index: int,
    ) -> SelectedQuestion:
        source_id = _clean_text(
            raw_question.get("id"), f"questions[{index}].id"
        )
        category = _clean_text(
            raw_question.get("category"), f"{source_id}.category"
        ).lower()
        level = _clean_text(
            raw_question.get("level"), f"{source_id}.level"
        ).lower()
        question = _clean_text(
            raw_question.get("question"), f"{source_id}.question"
        )
        answer = _clean_text(
            raw_question.get("answer"), f"{source_id}.answer"
        )
        explanation = _clean_text(
            raw_question.get("explanation"), f"{source_id}.explanation"
        )
        source_name = _clean_text(
            raw_question.get("source_name", "unknown"),
            f"{source_id}.source_name",
        )
        source_url = _clean_text(
            raw_question.get("source_url", "https://example.invalid"),
            f"{source_id}.source_url",
        )
        quality_score = raw_question.get("quality_score", 0)

        if not isinstance(quality_score, (int, float)) or isinstance(
            quality_score, bool
        ):
            raise QuizContentBuildError(
                f"{source_id}.quality_score는 숫자여야 합니다."
            )

        return SelectedQuestion(
            source_id=source_id,
            category=category,
            level=level,
            question=question,
            answer=answer,
            explanation=explanation,
            quality_score=float(quality_score),
            source_name=source_name,
            source_url=source_url,
        )
