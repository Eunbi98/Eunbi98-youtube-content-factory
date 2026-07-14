from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


class FactValidationError(ValueError):
    """Question Pool 검증 입력 또는 결과가 올바르지 않을 때 발생합니다."""


_ALLOWED_LEVELS = {"elementary", "middle", "high", "current"}
_ALLOWED_STYLES = {"direct", "cloze", "description"}
_QUESTION_ID_PATTERN = re.compile(r"^quiz_\d{6}$")
_QUESTION_END_PATTERN = re.compile(r"[?？]$")
_NORMALIZE_PATTERN = re.compile(r"[^0-9a-z가-힣]")


def _clean_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str):
        raise FactValidationError(f"{field_name}은 문자열이어야 합니다.")

    cleaned = " ".join(value.strip().split())

    if not cleaned:
        raise FactValidationError(f"{field_name}은 비어 있을 수 없습니다.")

    return cleaned


def _normalize_text(value: str) -> str:
    return _NORMALIZE_PATTERN.sub("", value.lower())


def _number(value: Any, field_name: str) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise FactValidationError(f"{field_name}은 숫자여야 합니다.")

    return float(value)


def _parse_iso_datetime(value: str, field_name: str) -> datetime:
    normalized = value.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise FactValidationError(
            f"{field_name}은 ISO 8601 날짜 형식이어야 합니다: {value}"
        ) from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)

    return parsed.astimezone(timezone.utc)


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
        }


@dataclass(frozen=True)
class ValidationResult:
    status: str
    score: float
    issues: tuple[ValidationIssue, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "score": self.score,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class QuestionPoolValidator:
    def validate_file(
        self,
        *,
        input_path: Path,
        output_path: Path,
        report_path: Path,
        minimum_validation_score: float,
        reject_warnings: bool,
    ) -> dict[str, Any]:
        if not 0 <= minimum_validation_score <= 100:
            raise FactValidationError(
                "minimum_validation_score는 0~100 사이여야 합니다."
            )

        raw_pool = self._load_json(input_path)
        raw_questions = raw_pool.get("questions")

        if not isinstance(raw_questions, list) or not raw_questions:
            raise FactValidationError(
                "question_pool.questions는 비어 있지 않은 배열이어야 합니다."
            )

        validated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        seen_hashes: set[str] = set()
        seen_question_answer: set[str] = set()
        validated_questions: list[dict[str, Any]] = []
        rejected_questions: list[dict[str, Any]] = []

        for index, raw_question in enumerate(raw_questions, start=1):
            normalized, result = self._validate_question(
                raw_question,
                index=index,
                seen_hashes=seen_hashes,
                seen_question_answer=seen_question_answer,
                validated_at=validated_at,
            )

            warning_count = sum(
                1 for issue in result.issues if issue.severity == "warning"
            )
            error_count = sum(
                1 for issue in result.issues if issue.severity == "error"
            )
            accepted = (
                error_count == 0
                and result.score >= minimum_validation_score
                and (not reject_warnings or warning_count == 0)
            )

            normalized["validation"] = {
                **result.to_dict(),
                "accepted": accepted,
                "validated_at": validated_at,
            }

            if accepted:
                validated_questions.append(normalized)
            else:
                rejected_questions.append(normalized)

        output_payload = dict(raw_pool)
        output_payload["version"] = "1.1"
        output_payload["validated_at"] = validated_at
        output_payload["minimum_validation_score"] = minimum_validation_score
        output_payload["question_count"] = len(validated_questions)
        output_payload["questions"] = validated_questions

        report_payload = {
            "version": "1.0",
            "validated_at": validated_at,
            "input": str(input_path.resolve()),
            "output": str(output_path.resolve()),
            "minimum_validation_score": minimum_validation_score,
            "reject_warnings": reject_warnings,
            "input_count": len(raw_questions),
            "accepted_count": len(validated_questions),
            "rejected_count": len(rejected_questions),
            "accepted_ids": [item.get("id") for item in validated_questions],
            "rejected": [
                {
                    "id": item.get("id"),
                    "question": item.get("question"),
                    "validation": item.get("validation"),
                }
                for item in rejected_questions
            ],
        }

        if not validated_questions:
            raise FactValidationError(
                "검증 기준을 통과한 Question이 없습니다. "
                f"minimum_validation_score={minimum_validation_score}"
            )

        self._save_json(output_path, output_payload)
        self._save_json(report_path, report_payload)
        return report_payload

    @staticmethod
    def _load_json(path: Path) -> dict[str, Any]:
        resolved = path.resolve()

        try:
            raw_data: Any = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise FactValidationError(
                "Question Pool을 읽지 못했습니다.\n"
                f"파일: {resolved}\n원인: {exc}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise FactValidationError("Question Pool 최상위 값은 객체여야 합니다.")

        return raw_data

    @staticmethod
    def _save_json(path: Path, payload: dict[str, Any]) -> None:
        resolved = path.resolve()
        resolved.parent.mkdir(parents=True, exist_ok=True)
        temporary = resolved.with_suffix(resolved.suffix + ".tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(resolved)

    def _validate_question(
        self,
        raw_question: Any,
        *,
        index: int,
        seen_hashes: set[str],
        seen_question_answer: set[str],
        validated_at: str,
    ) -> tuple[dict[str, Any], ValidationResult]:
        if not isinstance(raw_question, dict):
            raise FactValidationError(
                f"questions[{index}]은 객체여야 합니다."
            )

        question_id = _clean_text(raw_question.get("id"), f"questions[{index}].id")
        fact_id = _clean_text(
            raw_question.get("fact_id"), f"{question_id}.fact_id"
        )
        level = _clean_text(raw_question.get("level"), f"{question_id}.level").lower()
        category = _clean_text(
            raw_question.get("category"), f"{question_id}.category"
        ).lower()
        question = _clean_text(
            raw_question.get("question"), f"{question_id}.question"
        )
        answer = _clean_text(raw_question.get("answer"), f"{question_id}.answer")
        explanation = _clean_text(
            raw_question.get("explanation"), f"{question_id}.explanation"
        )
        question_style = _clean_text(
            raw_question.get("question_style"), f"{question_id}.question_style"
        ).lower()
        source_id = _clean_text(
            raw_question.get("source_id"), f"{question_id}.source_id"
        )
        source_name = _clean_text(
            raw_question.get("source_name"), f"{question_id}.source_name"
        )
        source_url = _clean_text(
            raw_question.get("source_url"), f"{question_id}.source_url"
        )
        verified_at = _clean_text(
            raw_question.get("verified_at"), f"{question_id}.verified_at"
        )
        question_hash = _clean_text(
            raw_question.get("question_hash"), f"{question_id}.question_hash"
        )
        quality_score = _number(
            raw_question.get("quality_score"), f"{question_id}.quality_score"
        )
        fact_quality_score = _number(
            raw_question.get("fact_quality_score"),
            f"{question_id}.fact_quality_score",
        )

        raw_keywords = raw_question.get("keywords")

        if not isinstance(raw_keywords, list):
            raise FactValidationError(f"{question_id}.keywords는 배열이어야 합니다.")

        keywords = [
            _clean_text(item, f"{question_id}.keywords").lower()
            for item in raw_keywords
        ]
        normalized = dict(raw_question)
        normalized.update(
            {
                "id": question_id,
                "fact_id": fact_id,
                "level": level,
                "category": category,
                "question": question,
                "answer": answer,
                "explanation": explanation,
                "question_style": question_style,
                "keywords": list(dict.fromkeys(keywords)),
                "source_id": source_id,
                "source_name": source_name,
                "source_url": source_url,
                "verified_at": verified_at,
                "question_hash": question_hash,
                "quality_score": round(quality_score, 2),
                "fact_quality_score": round(fact_quality_score, 2),
            }
        )

        issues: list[ValidationIssue] = []
        score = 100.0

        def add_issue(code: str, severity: str, message: str, penalty: float) -> None:
            nonlocal score
            issues.append(ValidationIssue(code, severity, message))
            score -= penalty

        if not _QUESTION_ID_PATTERN.fullmatch(question_id):
            add_issue(
                "invalid_question_id",
                "error",
                "Question ID는 quiz_000001 형식이어야 합니다.",
                30,
            )

        if level not in _ALLOWED_LEVELS:
            add_issue(
                "invalid_level",
                "error",
                f"지원하지 않는 난이도입니다: {level}",
                30,
            )

        if question_style not in _ALLOWED_STYLES:
            add_issue(
                "invalid_question_style",
                "error",
                f"지원하지 않는 문제 형식입니다: {question_style}",
                20,
            )

        if not _QUESTION_END_PATTERN.search(question):
            add_issue(
                "missing_question_mark",
                "warning",
                "질문이 물음표로 끝나지 않습니다.",
                8,
            )

        if len(question) < 8:
            add_issue(
                "question_too_short",
                "warning",
                "질문이 지나치게 짧습니다.",
                12,
            )
        elif len(question) > 80:
            add_issue(
                "question_too_long",
                "warning",
                "질문이 영상 자막에 사용하기에는 깁니다.",
                8,
            )

        if len(answer) > 35:
            add_issue(
                "answer_too_long",
                "warning",
                "정답이 단답형으로 사용하기에는 깁니다.",
                12,
            )

        if len(explanation) < 10:
            add_issue(
                "explanation_too_short",
                "warning",
                "해설이 사실 검증 근거로 사용하기에는 짧습니다.",
                8,
            )
        elif len(explanation) > 180:
            add_issue(
                "explanation_too_long",
                "warning",
                "해설이 영상용으로 사용하기에는 깁니다.",
                5,
            )

        normalized_answer = _normalize_text(answer)
        normalized_question = _normalize_text(question)

        if normalized_answer and normalized_answer in normalized_question:
            add_issue(
                "answer_exposed_in_question",
                "error",
                "질문 본문에 정답이 그대로 노출됩니다.",
                35,
            )

        parsed_url = urlparse(source_url)

        if parsed_url.scheme != "https" or not parsed_url.netloc:
            add_issue(
                "invalid_source_url",
                "error",
                "출처 URL은 유효한 HTTPS 주소여야 합니다.",
                35,
            )

        try:
            verified_date = _parse_iso_datetime(
                verified_at, f"{question_id}.verified_at"
            )
            validation_date = _parse_iso_datetime(
                validated_at, f"{question_id}.validated_at"
            )
            age_days = (validation_date - verified_date).days

            if level == "current" and age_days > 30:
                add_issue(
                    "stale_current_fact",
                    "error",
                    f"시사 문제 검증일이 {age_days}일 경과했습니다.",
                    35,
                )
            elif level != "current" and age_days > 365:
                add_issue(
                    "old_verification",
                    "warning",
                    f"마지막 검증 후 {age_days}일이 경과했습니다.",
                    8,
                )
        except FactValidationError as exc:
            add_issue("invalid_verified_at", "error", str(exc), 25)

        if quality_score < 70:
            add_issue(
                "low_question_quality",
                "warning",
                f"Question Generator 품질 점수가 낮습니다: {quality_score:.2f}",
                12,
            )

        if fact_quality_score < 70:
            add_issue(
                "low_fact_quality",
                "error",
                f"원본 Fact 품질 점수가 낮습니다: {fact_quality_score:.2f}",
                25,
            )

        if len(normalized["keywords"]) < 2:
            add_issue(
                "insufficient_keywords",
                "warning",
                "미디어 검색용 키워드가 2개 미만입니다.",
                5,
            )

        duplicate_key = f"{normalized_question}::{normalized_answer}"

        if question_hash in seen_hashes or duplicate_key in seen_question_answer:
            add_issue(
                "duplicate_question",
                "error",
                "Question Pool 안에 중복 문제가 있습니다.",
                50,
            )

        seen_hashes.add(question_hash)
        seen_question_answer.add(duplicate_key)

        error_count = sum(1 for issue in issues if issue.severity == "error")
        warning_count = sum(1 for issue in issues if issue.severity == "warning")

        if error_count:
            status = "rejected"
        elif warning_count:
            status = "warning"
        else:
            status = "verified"

        return normalized, ValidationResult(
            status=status,
            score=round(max(0.0, score), 2),
            issues=tuple(issues),
        )
