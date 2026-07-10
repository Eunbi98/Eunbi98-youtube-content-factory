from __future__ import annotations

from dataclasses import dataclass
import re


KOREAN_PARTICLES = (
    "은",
    "는",
    "이",
    "가",
    "을",
    "를",
    "에",
    "에서",
    "에게",
    "께",
    "께서",
    "로",
    "으로",
    "와",
    "과",
    "도",
    "만",
    "부터",
    "까지",
    "보다",
    "처럼",
    "의",
    "라고",
    "이라고",
)

WEAK_LINE_STARTERS = (
    "그리고",
    "하지만",
    "그래서",
    "또",
    "즉",
    "이",
    "그",
    "저",
)

WEAK_LINE_ENDINGS = (
    "그리고",
    "하지만",
    "때문에",
    "먼저",
    "다시",
    "약",
)

NUMBER_PATTERN = re.compile(r"\d+(?:[~.-]\d+(?:\.\d+)?)?%?(?:일|년|개월|cm|kg)?")
ENGLISH_WORD_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9.-]*")


@dataclass(frozen=True)
class CaptionLayoutConfig:
    one_line_max: int = 28
    preferred_min: int = 14
    preferred_max: int = 18
    two_line_max: int = 56
    min_second_line: int = 8


class CaptionDirector:
    def __init__(self, config: CaptionLayoutConfig | None = None) -> None:
        self.config = config or CaptionLayoutConfig()

    def layout(self, text: str) -> str:
        cleaned = self._normalize(text)

        if not cleaned:
            return ""

        if len(cleaned) <= self.config.one_line_max:
            return cleaned

        shortened = cleaned[: self.config.two_line_max].rstrip()
        candidates = self._split_candidates(shortened)

        if not candidates:
            return shortened

        first, second = min(candidates, key=self._score_candidate)
        return f"{first}\n{second}"

    def _normalize(self, text: str) -> str:
        cleaned = re.sub(r"\s+", " ", str(text or "")).strip()
        cleaned = re.sub(r"\s*~\s*", "~", cleaned)
        cleaned = re.sub(r"(\d)\s*%\b", r"\1%", cleaned)
        return cleaned

    def _split_candidates(self, text: str) -> list[tuple[str, str]]:
        candidates = self._word_boundary_candidates(text)

        if candidates:
            return candidates

        return self._character_boundary_candidates(text)

    def _word_boundary_candidates(self, text: str) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []

        for match in re.finditer(r"\s+", text):
            split_at = match.start()
            first = text[:split_at].strip()
            second = text[match.end():].strip()

            if self._is_bad_candidate(text, split_at, first, second):
                continue

            candidates.append((first, second))

        return candidates

    def _character_boundary_candidates(self, text: str) -> list[tuple[str, str]]:
        candidates: list[tuple[str, str]] = []

        for split_at in range(1, len(text)):
            first = text[:split_at].strip()
            second = text[split_at:].strip()

            if self._is_bad_candidate(text, split_at, first, second):
                continue

            candidates.append((first, second))

        return candidates

    def _is_bad_candidate(
        self,
        text: str,
        split_at: int,
        first: str,
        second: str,
    ) -> bool:
        if not first or not second:
            return True

        if "\n" in first or "\n" in second:
            return True

        if len(second) < self.config.min_second_line:
            return True

        if self._breaks_protected_token(text, split_at):
            return True

        if self._separates_english_words(text, split_at):
            return True

        if self._separates_particle(first, second):
            return True

        if self._has_weak_edge(first, second):
            return True

        return False

    def _breaks_protected_token(self, text: str, split_at: int) -> bool:
        return any(
            match.start() < split_at < match.end()
            for pattern in (NUMBER_PATTERN, ENGLISH_WORD_PATTERN)
            for match in pattern.finditer(text)
        )

    def _separates_english_words(self, text: str, split_at: int) -> bool:
        left = self._previous_non_space(text, split_at)
        right = self._next_non_space(text, split_at)
        return bool(left and right and left.isascii() and right.isascii())

    def _separates_particle(self, first: str, second: str) -> bool:
        if second.startswith(KOREAN_PARTICLES):
            return True

        last_word = first.split()[-1]

        if len(last_word) == 1 and last_word in KOREAN_PARTICLES:
            return True

        return False

    def _has_weak_edge(self, first: str, second: str) -> bool:
        first_last = first.split()[-1]
        second_first = second.split()[0]

        if first_last in WEAK_LINE_ENDINGS:
            return True

        if second_first in WEAK_LINE_STARTERS and len(second) < self.config.preferred_min:
            return True

        return False

    def _score_candidate(self, candidate: tuple[str, str]) -> int:
        first, second = candidate
        first_len = len(first)
        second_len = len(second)

        balance_penalty = abs(first_len - second_len) * 3
        preferred_penalty = (
            self._outside_penalty(first_len)
            + self._outside_penalty(second_len)
        ) * 5
        short_second_penalty = 120 if second_len < self.config.preferred_min else 0
        long_line_penalty = 80 if max(first_len, second_len) > self.config.one_line_max else 0

        return (
            balance_penalty
            + preferred_penalty
            + short_second_penalty
            + long_line_penalty
        )

    def _outside_penalty(self, value: int) -> int:
        if value < self.config.preferred_min:
            return self.config.preferred_min - value

        if value > self.config.preferred_max:
            return value - self.config.preferred_max

        return 0

    def _previous_non_space(self, text: str, split_at: int) -> str:
        for index in range(split_at - 1, -1, -1):
            if not text[index].isspace():
                return text[index]
        return ""

    def _next_non_space(self, text: str, split_at: int) -> str:
        for index in range(split_at, len(text)):
            if not text[index].isspace():
                return text[index]
        return ""


def layout_caption_text(
    text: str,
    one_line_max: int = 28,
    preferred_min: int = 14,
    preferred_max: int = 18,
    two_line_max: int = 56,
    min_second_line: int = 8,
) -> str:
    director = CaptionDirector(
        CaptionLayoutConfig(
            one_line_max=one_line_max,
            preferred_min=preferred_min,
            preferred_max=preferred_max,
            two_line_max=two_line_max,
            min_second_line=min_second_line,
        )
    )
    return director.layout(text)


def calculate_caption_box(
    wrapped_text: str,
    screen_width: int,
    font_size: int,
    padding_x: int = 56,
    padding_y: int = 24,
    min_width_ratio: float = 0.55,
    max_width_ratio: float = 0.88,
) -> dict[str, int]:
    lines = [
        line.strip()
        for line in str(wrapped_text or "").splitlines()
        if line.strip()
    ] or [""]
    longest_line = max(len(line) for line in lines)
    estimated_text_width = int(longest_line * font_size * 0.58)
    estimated_text_height = int(len(lines) * font_size * 1.18)
    min_width = int(screen_width * min_width_ratio)
    max_width = int(screen_width * max_width_ratio)
    width = min(
        max_width,
        max(min_width, estimated_text_width + (padding_x * 2)),
    )
    height = max(
        int(font_size * 1.65),
        estimated_text_height + (padding_y * 2),
    )

    return {
        "width": width,
        "height": height,
        "line_count": len(lines),
        "longest_line": longest_line,
    }
