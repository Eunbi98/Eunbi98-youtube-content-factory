from __future__ import annotations

import logging
import re

from app.story.text_normalizer import normalize_english_terms


logger = logging.getLogger(__name__)


class ScriptQAEngine:
    """Polish Story Engine scripts for Korean Shorts subtitles."""

    def __init__(
        self,
        min_chars: int = 8,
        target_chars: int = 23,
        max_chars: int = 25,
        hard_max_chars: int = 30,
    ) -> None:
        self.min_chars = min_chars
        self.target_chars = target_chars
        self.max_chars = max_chars
        self.hard_max_chars = hard_max_chars

    def polish_script(
        self,
        script: str,
        protected_first: str = "",
        protected_last: str = "",
    ) -> str:
        first = self._clean_line(protected_first)
        last = self._clean_line(protected_last)
        body_lines = self._extract_body_lines(script, first, last)
        polished_body = self.polish_lines(body_lines)

        lines = []

        if first:
            lines.append(first)

        lines.extend(polished_body)

        if last and last not in lines[-1:]:
            lines.append(last)

        logger.info("Script QA polished %s lines", len(lines))
        return "\n".join(lines)

    def polish_lines(self, lines: list[str]) -> list[str]:
        text = " ".join(
            self._clean_line(line)
            for line in lines
            if self._clean_line(line)
        )
        sentences = self._split_sentences(text)
        polished = []

        for sentence in sentences:
            polished.extend(self._split_by_meaning(sentence))

        polished = self._repair_auxiliary_breaks(polished)
        polished = self._merge_short_lines(polished)

        return [
            line
            for line in polished
            if line
        ]

    def _extract_body_lines(
        self,
        script: str,
        protected_first: str,
        protected_last: str,
    ) -> list[str]:
        lines = [
            self._clean_line(line)
            for line in str(script or "").splitlines()
            if self._clean_line(line)
        ]

        if protected_first and lines and lines[0] == protected_first:
            lines = lines[1:]

        if protected_last and lines and lines[-1] == protected_last:
            lines = lines[:-1]

        return lines

    def _split_sentences(self, text: str) -> list[str]:
        text = self._remove_stage_directions(text)
        text = re.sub(r"\s+", " ", text).strip()

        if not text:
            return []

        marked = re.sub(r"([.!?。？！])", r"\1\n", text)

        return [
            sentence.strip()
            for sentence in re.split(r"\n|[•·]", marked)
            if sentence.strip()
        ]

    def _split_by_meaning(self, sentence: str) -> list[str]:
        sentence = self._clean_line(sentence)

        if not sentence:
            return []

        if len(sentence) <= self.max_chars:
            return [sentence]

        words = sentence.split()

        if len(words) <= 1:
            return self._split_long_word(sentence)

        chunks = []
        current = ""

        for word in words:
            candidate = f"{current} {word}".strip()

            if len(candidate) <= self.max_chars:
                current = candidate
                continue

            before, bridge = self._detach_trailing_bridge(current)

            if before:
                chunks.append(before)

            current = f"{bridge} {word}".strip() if bridge else word

        if current:
            chunks.append(current)

        return self._repair_auxiliary_breaks(chunks)

    def _detach_trailing_bridge(self, text: str) -> tuple[str, str]:
        words = text.split()

        if not words:
            return "", ""

        dangling_phrases = {
            "알 수",
            "할 수",
            "될 수",
            "볼 수",
            "갈 수",
            "생길 수",
            "나올 수",
            "바뀔 수",
            "커질 수",
        }
        dangling_words = {
            "수",
            "알",
            "할",
            "될",
            "볼",
            "갈",
            "줄",
            "것",
            "때",
            "중",
            "뒤",
            "앞",
        }
        dangling_suffixes = (
            "다고",
            "라고",
            "필요하다고",
            "중요하다고",
            "되어야",
            "해야",
            "하고",
        )

        two_word_bridge = " ".join(words[-2:])

        if len(words) >= 2 and words[-1] == "수":
            return " ".join(words[:-2]), two_word_bridge

        if len(words) >= 2 and two_word_bridge in dangling_phrases:
            return " ".join(words[:-2]), two_word_bridge

        last_word = words[-1]

        if (
            last_word in dangling_words
            or last_word.endswith(dangling_suffixes)
        ):
            return " ".join(words[:-1]), last_word

        return text, ""

    def _split_long_word(self, text: str) -> list[str]:
        return [
            text[index:index + self.max_chars].strip()
            for index in range(0, len(text), self.max_chars)
            if text[index:index + self.max_chars].strip()
        ]

    def _repair_auxiliary_breaks(self, lines: list[str]) -> list[str]:
        repaired = []
        index = 0

        while index < len(lines):
            current = lines[index].strip()

            if (
                index + 1 < len(lines)
                and (
                    self._is_dangling_end(current)
                    or lines[index + 1].strip().startswith("수 ")
                )
            ):
                combined = f"{current} {lines[index + 1].strip()}".strip()
                repaired.extend(self._split_by_meaning(combined))
                index += 2
                continue

            repaired.append(current)
            index += 1

        return repaired

    def _merge_short_lines(self, lines: list[str]) -> list[str]:
        merged = []
        index = 0

        while index < len(lines):
            current = lines[index].strip()

            if not current:
                index += 1
                continue

            if (
                len(current) < self.min_chars
                and index + 1 < len(lines)
            ):
                candidate = f"{current} {lines[index + 1].strip()}".strip()

                if len(candidate) <= self.max_chars:
                    merged.append(candidate)
                    index += 2
                    continue

            if (
                len(current) < self.min_chars
                and merged
                and len(f"{merged[-1]} {current}") <= self.max_chars
            ):
                merged[-1] = f"{merged[-1]} {current}".strip()
            else:
                merged.append(current)

            index += 1

        return merged

    def _is_dangling_end(self, text: str) -> bool:
        normalized = text.strip()
        words = normalized.split()

        if not words:
            return False

        dangling_words = {
            "수",
            "알",
            "할",
            "될",
            "볼",
            "갈",
            "줄",
            "것",
            "때",
            "중",
            "뒤",
            "앞",
        }
        dangling_phrases = (
            "알 수",
            "할 수",
            "될 수",
            "볼 수",
            "갈 수",
            "생길 수",
            "나올 수",
            "바뀔 수",
            "커질 수",
        )
        dangling_suffixes = (
            "다고",
            "라고",
            "필요하다고",
            "중요하다고",
        )

        return (
            words[-1] in dangling_words
            or normalized.endswith(dangling_phrases)
            or normalized.endswith(dangling_suffixes)
        )

    def _clean_line(self, line: str) -> str:
        line = normalize_english_terms(line)
        line = self._remove_stage_directions(line)
        line = re.sub(r"^\s*[-*\d.)]+\s*", "", line)
        line = re.sub(r"\s+", " ", line)
        line = line.strip()
        return line

    def _remove_stage_directions(self, text: str) -> str:
        banned_words = [
            "음악 삽입",
            "장면 전환",
            "BGM",
            "효과음",
            "자막 표시",
            "자막 지시",
            "화면 지시",
            "이미지 지시",
            "내레이션",
            "컷",
        ]

        cleaned = str(text or "")

        for word in banned_words:
            escaped = re.escape(word)
            cleaned = re.sub(
                rf"\([^)]*{escaped}[^)]*\)",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(
                rf"\[[^\]]*{escaped}[^\]]*\]",
                "",
                cleaned,
                flags=re.IGNORECASE,
            )
            cleaned = re.sub(
                escaped,
                "",
                cleaned,
                flags=re.IGNORECASE,
            )

        return cleaned
