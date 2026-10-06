from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from question_models import (
    QuestionDataError,
    QuestionPool,
    QuestionRecord,
    clean_text,
    make_question_hash,
)


DIRECT_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(r"^(?P<prefix>.+?)(?:은|는)\s*(?P<answer>.+?)(?:이다|입니다)\.?$"),
        "{prefix}은 무엇일까요?",
    ),
    (
        re.compile(r"^(?P<prefix>.+?)(?:을|를)\s*(?P<answer>.+?)(?:이라고|라고)\s*한다\.?$"),
        "{prefix}을 무엇이라고 할까요?",
    ),
    (
        re.compile(r"^(?P<prefix>.+?)\s*(?P<answer>.+?)(?:이라고|라고)\s*한다\.?$"),
        "{prefix} 무엇이라고 할까요?",
    ),
)


class QuestionGenerator:
    def generate_from_file(
        self,
        *,
        fact_pool_path: Path,
        minimum_quality: float,
        limit: int,
    ) -> QuestionPool:
        if not 0 <= minimum_quality <= 100:
            raise QuestionDataError("minimum_quality는 0~100 사이여야 합니다.")

        if limit <= 0:
            raise QuestionDataError("limit은 1 이상이어야 합니다.")

        raw_pool = self._load_json(fact_pool_path)
        level = clean_text(raw_pool.get("level"), "fact_pool.level").lower()
        raw_categories = raw_pool.get("categories")
        raw_facts = raw_pool.get("facts")

        if not isinstance(raw_categories, list) or not raw_categories:
            raise QuestionDataError("fact_pool.categories는 비어 있지 않은 배열이어야 합니다.")

        if not isinstance(raw_facts, list) or not raw_facts:
            raise QuestionDataError("fact_pool.facts는 비어 있지 않은 배열이어야 합니다.")

        categories = {
            clean_text(item, "fact_pool.categories").lower()
            for item in raw_categories
        }

        generated: list[QuestionRecord] = []

        for index, raw_fact in enumerate(raw_facts, start=1):
            question = self._build_record(raw_fact, index=index)

            if question.quality_score >= minimum_quality:
                generated.append(question)

        deduplicated: dict[str, QuestionRecord] = {}

        for item in generated:
            existing = deduplicated.get(item.question_hash)

            if existing is None or item.quality_score > existing.quality_score:
                deduplicated[item.question_hash] = item

        selected = sorted(
            deduplicated.values(),
            key=lambda item: (-item.quality_score, item.id),
        )[:limit]

        if not selected:
            raise QuestionDataError(
                "품질 기준을 통과한 Question이 없습니다. "
                f"minimum_quality={minimum_quality}"
            )

        return QuestionPool.create(
            level=level,
            categories=categories,
            minimum_quality=minimum_quality,
            questions=selected,
        )

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        resolved = path.resolve()

        try:
            raw_data: Any = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise QuestionDataError(
                "Fact Pool을 읽지 못했습니다.\n"
                f"파일: {resolved}\n원인: {exc}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise QuestionDataError("Fact Pool 최상위 값은 객체여야 합니다.")

        return raw_data

    def _build_record(
        self,
        raw_fact: Any,
        *,
        index: int,
    ) -> QuestionRecord:
        if not isinstance(raw_fact, dict):
            raise QuestionDataError("fact_pool.facts의 각 항목은 객체여야 합니다.")

        fact_id = clean_text(raw_fact.get("id"), "fact.id")
        level = clean_text(raw_fact.get("level"), f"{fact_id}.level").lower()
        category = clean_text(
            raw_fact.get("category"),
            f"{fact_id}.category",
        ).lower()
        fact = clean_text(raw_fact.get("fact"), f"{fact_id}.fact")
        answer = clean_text(raw_fact.get("answer"), f"{fact_id}.answer")
        explanation = clean_text(
            raw_fact.get("explanation"),
            f"{fact_id}.explanation",
        )
        source_id = clean_text(
            raw_fact.get("source_id"),
            f"{fact_id}.source_id",
        )
        source_name = clean_text(
            raw_fact.get("source_name"),
            f"{fact_id}.source_name",
        )
        source_url = clean_text(
            raw_fact.get("source_url"),
            f"{fact_id}.source_url",
        )
        verified_at = clean_text(
            raw_fact.get("verified_at"),
            f"{fact_id}.verified_at",
        )

        fact_quality_score = raw_fact.get("quality_score", 0)

        if not isinstance(fact_quality_score, (int, float)) or isinstance(
            fact_quality_score, bool
        ):
            raise QuestionDataError(f"{fact_id}.quality_score는 숫자여야 합니다.")

        raw_tags = raw_fact.get("tags", [])

        if not isinstance(raw_tags, list):
            raise QuestionDataError(f"{fact_id}.tags는 배열이어야 합니다.")

        keywords = tuple(
            dict.fromkeys(
                clean_text(tag, f"{fact_id}.tags").lower()
                for tag in raw_tags
            )
        )

        question, question_style = self._build_question(
            fact=fact,
            answer=answer,
        )
        quality_score = self._calculate_quality_score(
            question=question,
            answer=answer,
            explanation=explanation,
            question_style=question_style,
            keyword_count=len(keywords),
            fact_quality_score=float(fact_quality_score),
            source_url=source_url,
        )

        return QuestionRecord(
            id=f"quiz_{index:06d}",
            fact_id=fact_id,
            level=level,
            category=category,
            question=question,
            answer=answer,
            explanation=explanation,
            question_style=question_style,
            keywords=keywords,
            source_id=source_id,
            source_name=source_name,
            source_url=source_url,
            published_at=self._optional_text(raw_fact.get("published_at")),
            verified_at=verified_at,
            evergreen=bool(raw_fact.get("evergreen", level != "current")),
            fact_quality_score=round(float(fact_quality_score), 2),
            quality_score=quality_score,
            question_hash=make_question_hash(question, answer),
        )

    def _build_question(self, *, fact: str, answer: str) -> tuple[str, str]:
        normalized_fact = fact.rstrip(".。!? ")

        for pattern, template in DIRECT_PATTERNS:
            match = pattern.match(normalized_fact)

            if match is None:
                continue

            matched_answer = match.group("answer").strip()

            if self._same_answer(matched_answer, answer):
                prefix = match.group("prefix").strip()
                question = template.format(prefix=prefix)
                return self._normalize_question(question), "direct"

        masked = self._mask_answer(normalized_fact, answer)

        if masked is not None:
            return (
                self._normalize_question(
                    f"빈칸에 들어갈 말은 무엇일까요? {masked}"
                ),
                "cloze",
            )

        return (
            self._normalize_question(
                f"다음 설명에 해당하는 답은 무엇일까요? {normalized_fact}"
            ),
            "description",
        )

    @staticmethod
    def _same_answer(left: str, right: str) -> bool:
        normalize = lambda value: re.sub(r"[^0-9a-z가-힣]", "", value.lower())
        return normalize(left) == normalize(right)

    @staticmethod
    def _mask_answer(fact: str, answer: str) -> str | None:
        position = fact.find(answer)

        if position < 0:
            return None

        masked = fact[:position] + "□" + fact[position + len(answer) :]
        return " ".join(masked.split())

    @staticmethod
    def _normalize_question(question: str) -> str:
        cleaned = " ".join(question.split())
        cleaned = re.sub(r"\?+$", "", cleaned)
        return cleaned + "?"

    @staticmethod
    def _optional_text(value: Any) -> str | None:
        if value is None:
            return None

        return clean_text(value, "published_at")

    @staticmethod
    def _calculate_quality_score(
        *,
        question: str,
        answer: str,
        explanation: str,
        question_style: str,
        keyword_count: int,
        fact_quality_score: float,
        source_url: str,
    ) -> float:
        score = min(45.0, fact_quality_score * 0.45)

        if 10 <= len(question) <= 55:
            score += 22
        elif len(question) <= 80:
            score += 14
        else:
            score += 5

        if 1 <= len(answer) <= 20:
            score += 12
        elif len(answer) <= 35:
            score += 7

        if 12 <= len(explanation) <= 100:
            score += 10
        elif len(explanation) <= 160:
            score += 6

        if question_style == "direct":
            score += 6
        elif question_style == "cloze":
            score += 4
        else:
            score += 2

        if keyword_count >= 2:
            score += 3

        if source_url.startswith("https://"):
            score += 2

        return round(min(100.0, score), 2)
