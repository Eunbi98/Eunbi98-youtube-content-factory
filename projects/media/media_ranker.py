from __future__ import annotations

import re
from dataclasses import replace
from typing import Iterable

from provider_models import MediaCandidate


NEGATIVE_TERMS = {
    "station",
    "booking office",
    "railway",
    "subway",
    "metro",
    "entrance",
    "sign",
    "logo",
    "poster",
    "map",
    "diagram",
    "chart",
    "advertisement",
}

ANCIENT_TERMS = {
    "ancient",
    "archaeological",
    "archaeology",
    "ruins",
    "underground city",
    "subterranean city",
    "lost city",
    "cave",
    "tunnel",
    "temple",
    "civilization",
}

SPACE_TERMS = {
    "nasa",
    "mars",
    "moon",
    "space",
    "galaxy",
    "asteroid",
    "planet",
    "solar",
    "astronaut",
}


def tokenize(text: str) -> set[str]:
    return {
        token
        for token in re.findall(
            r"[a-z0-9]+",
            text.casefold(),
        )
        if len(token) >= 2
    }


def rerank_candidates(
    *,
    query: str,
    candidates: Iterable[
        MediaCandidate
    ],
) -> list[MediaCandidate]:
    query_tokens = tokenize(query)
    query_text = query.casefold()

    wants_ancient = any(
        term in query_text
        for term in ANCIENT_TERMS
    )

    wants_space = any(
        term in query_text
        for term in SPACE_TERMS
    )

    ranked: list[MediaCandidate] = []

    for candidate in candidates:
        haystack = " ".join(
            value
            for value in (
                candidate.title,
                candidate.description or "",
            )
            if value
        ).casefold()

        score = float(candidate.score)

        matched = sum(
            1
            for token in query_tokens
            if token in haystack
        )

        score += matched * 18.0

        if candidate.orientation == "portrait":
            score += 18.0
        elif candidate.orientation == "square":
            score += 7.0

        if (
            candidate.width >= 1080
            and candidate.height >= 1080
        ):
            score += 10.0

        if any(
            term in haystack
            for term in NEGATIVE_TERMS
        ):
            score -= 80.0

        if wants_ancient:
            ancient_matches = sum(
                1
                for term in ANCIENT_TERMS
                if term in haystack
            )
            score += ancient_matches * 20.0

        if wants_space:
            if candidate.provider == "nasa":
                score += 35.0
            space_matches = sum(
                1
                for term in SPACE_TERMS
                if term in haystack
            )
            score += space_matches * 16.0

        ranked.append(
            replace(
                candidate,
                score=round(score, 3),
            )
        )

    ranked.sort(
        key=lambda item: (
            -item.score,
            -item.width * item.height,
            item.title.casefold(),
        )
    )

    return ranked
