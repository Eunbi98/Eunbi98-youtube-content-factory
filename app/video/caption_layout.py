from __future__ import annotations

import re


PROTECTED_PHRASES = (
    "알 수 없는",
    "할 수 있다",
    "할 수 있다고",
    "될 수 있다",
    "달라질 수 있다",
    "바꿀 수 있습니다",
    "필요하다고 말했다",
    "중요하다고 전했다",
    "라고 말했다",
    "다고 말했다",
    "라고 전했다",
    "다고 전했다",
)

DANGLING_ENDINGS = (
    "알 수",
    "할 수",
    "될 수",
    "달라질 수",
    "바꿀 수",
    "라고",
    "다고",
    "필요하다고",
    "중요하다고",
)


def layout_caption_text(
    text: str,
    one_line_max: int = 28,
    preferred_min: int = 18,
    preferred_max: int = 24,
    two_line_max: int = 56,
    min_second_line: int = 10,
) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip()

    if not cleaned:
        return ""

    if len(cleaned) <= one_line_max:
        return cleaned

    shortened = cleaned[:two_line_max].rstrip()
    candidates = _split_candidates(shortened)

    if not candidates:
        return shortened

    first, second = min(
        candidates,
        key=lambda item: _score_candidate(
            item[0],
            item[1],
            preferred_min=preferred_min,
            preferred_max=preferred_max,
            min_second_line=min_second_line,
        ),
    )
    return f"{first}\n{second}"


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


def _split_candidates(text: str) -> list[tuple[str, str]]:
    candidates = []

    for match in re.finditer(r"\s+", text):
        split_at = match.start()
        first = text[:split_at].strip()
        second = text[match.end():].strip()

        if not first or not second:
            continue

        if _breaks_protected_phrase(text, split_at):
            continue

        if _is_bad_break(first, second):
            continue

        candidates.append((first, second))

    return candidates


def _breaks_protected_phrase(text: str, split_at: int) -> bool:
    for phrase in PROTECTED_PHRASES:
        start = text.find(phrase)

        while start != -1:
            end = start + len(phrase)

            if start < split_at < end:
                return True

            start = text.find(phrase, start + 1)

    return False


def _is_bad_break(first: str, second: str) -> bool:
    if any(first.endswith(ending) for ending in DANGLING_ENDINGS):
        return True

    if second.startswith(("말했다", "전했다", "합니다", "있다", "있습니다")):
        return True

    return False


def _score_candidate(
    first: str,
    second: str,
    preferred_min: int,
    preferred_max: int,
    min_second_line: int,
) -> int:
    first_len = len(first)
    second_len = len(second)
    balance_penalty = abs(first_len - second_len) * 3
    range_penalty = (
        _outside_penalty(first_len, preferred_min, preferred_max)
        + _outside_penalty(second_len, preferred_min, preferred_max)
    ) * 2
    short_second_penalty = 300 if second_len < min_second_line else 0

    return balance_penalty + range_penalty + short_second_penalty


def _outside_penalty(value: int, minimum: int, maximum: int) -> int:
    if value < minimum:
        return minimum - value

    if value > maximum:
        return value - maximum

    return 0
