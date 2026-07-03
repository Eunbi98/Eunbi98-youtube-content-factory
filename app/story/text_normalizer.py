from __future__ import annotations

import re


TERM_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    (r"(?<![A-Za-z])NASA's(?![A-Za-z])", "나사의"),
    (r"(?<![A-Za-z])NASA(?![A-Za-z])", "나사"),
    (r"(?<![A-Za-z])Nasa(?![A-Za-z])", "나사"),
    (r"(?<![A-Za-z])James Webb Space Telescope(?![A-Za-z])", "제임스 웹 우주망원경"),
    (r"(?<![A-Za-z])James Webb Telescope(?![A-Za-z])", "제임스 웹 망원경"),
    (r"(?<![A-Za-z])James Webb Space(?![A-Za-z])", "제임스 웹 우주"),
    (r"(?<![A-Za-z])James Webb(?![A-Za-z])", "제임스 웹"),
    (r"(?<![A-Za-z])Webb Telescope(?![A-Za-z])", "웹 망원경"),
    (r"(?<![A-Za-z])FS Tau(?![A-Za-z])", "FS 타우"),
    (r"(?<![A-Za-z])Fs Tau(?![A-Za-z])", "FS 타우"),
)


def normalize_english_terms(text: str) -> str:
    normalized = str(text or "")

    for pattern, replacement in TERM_REPLACEMENTS:
        normalized = re.sub(
            pattern,
            replacement,
            normalized,
            flags=re.IGNORECASE,
        )

    normalized = normalized.replace("우주망원경가", "우주망원경이")
    normalized = normalized.replace("웹 망원경가", "웹 망원경이")

    return normalized
