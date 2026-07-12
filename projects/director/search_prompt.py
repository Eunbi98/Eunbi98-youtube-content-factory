from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Sequence


SearchIntent = Literal[
    "primary",
    "portrait",
    "wide",
    "detail",
    "aerial",
    "map",
    "atmosphere",
]


class SearchPromptError(ValueError):
    """미디어 검색 프롬프트 생성 오류입니다."""


@dataclass(
    frozen=True,
    slots=True,
)
class SearchQuery:
    query: str
    intent: SearchIntent
    priority: int

    def __post_init__(
        self,
    ) -> None:
        normalized_query = (
            normalize_search_text(
                self.query
            )
        )

        if not normalized_query:
            raise SearchPromptError(
                "검색어는 비어 있을 수 없습니다."
            )

        if self.priority < 1:
            raise SearchPromptError(
                "priority는 1 이상이어야 합니다."
            )

        object.__setattr__(
            self,
            "query",
            normalized_query,
        )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "query": self.query,
            "intent": self.intent,
            "priority": self.priority,
        }


@dataclass(
    frozen=True,
    slots=True,
)
class SceneSearchPrompt:
    scene_id: str
    title: str
    narration: str
    source_keywords: tuple[str, ...]
    queries: tuple[
        SearchQuery,
        ...,
    ]

    def __post_init__(
        self,
    ) -> None:
        normalized_scene_id = (
            self.scene_id.strip()
        )

        if not normalized_scene_id:
            raise SearchPromptError(
                "scene_id는 비어 있을 수 없습니다."
            )

        if not self.queries:
            raise SearchPromptError(
                f"{normalized_scene_id}: "
                "검색어가 생성되지 않았습니다."
            )

        object.__setattr__(
            self,
            "scene_id",
            normalized_scene_id,
        )

    @property
    def primary_query(
        self,
    ) -> str:
        return self.queries[0].query

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "sceneId": self.scene_id,
            "title": self.title,
            "narration": self.narration,
            "sourceKeywords": list(
                self.source_keywords
            ),
            "primaryQuery": (
                self.primary_query
            ),
            "queries": [
                query.to_dict()
                for query in self.queries
            ],
        }


# 한국어 핵심 표현을 실제 검색 가능한 영문 엔티티로 변환합니다.
ENTITY_ALIASES: dict[
    str,
    tuple[str, ...],
] = {
    "데린쿠유": (
        "Derinkuyu underground city",
        "Derinkuyu",
        "Cappadocia underground city",
    ),
    "지하도시": (
        "Derinkuyu underground city",
        "Cappadocia underground city",
        "ancient underground city Turkey",
    ),
    "지하 도시": (
        "Derinkuyu underground city",
        "Cappadocia underground city",
        "ancient underground city Turkey",
    ),
    "땅속 도시": (
        "Derinkuyu underground city",
        "ancient underground city",
        "Cappadocia tunnels",
    ),
    "땅속에 도시": (
        "Derinkuyu underground city",
        "ancient underground city",
        "Cappadocia underground city",
    ),
    "카파도키아": (
        "Cappadocia",
        "Cappadocia underground city",
        "Cappadocia Turkey",
    ),
    "폼페이": (
        "Pompeii ruins",
        "Pompeii archaeological site",
        "ancient Pompeii",
    ),
    "타이타닉": (
        "RMS Titanic",
        "Titanic ship",
        "Titanic wreck",
    ),
    "늑대": (
        "gray wolf",
        "wolf howling",
        "wild wolf",
    ),
    "피라미드": (
        "Egypt pyramids",
        "Great Pyramid of Giza",
        "ancient Egyptian pyramid",
    ),
    "화성": (
        "Mars planet",
        "Mars surface",
        "NASA Mars",
    ),
    "나사": (
        "NASA",
        "NASA space mission",
        "NASA spacecraft",
    ),
    "월드컵 트로피": (
        "FIFA World Cup Trophy",
        "World Cup trophy",
        "FIFA trophy",
    ),
    "사막": (
        "desert landscape",
        "sand dunes",
        "desert aerial view",
    ),
    "열돔": (
        "heat dome weather",
        "extreme heat map",
        "heatwave city",
    ),
    "폭염": (
        "extreme heatwave",
        "heatwave city",
        "global heat map",
    ),
    "물고기 비": (
        "fish rain phenomenon",
        "animals falling from sky",
        "fish storm",
    ),
}


INTENT_SUFFIXES: dict[
    SearchIntent,
    tuple[str, ...],
] = {
    "primary": (),
    "portrait": (
        "vertical",
    ),
    "wide": (
        "wide view",
    ),
    "detail": (
        "interior",
        "close up",
    ),
    "aerial": (
        "aerial view",
    ),
    "map": (
        "map",
    ),
    "atmosphere": (
        "cinematic",
    ),
}


def normalize_search_text(
    text: str,
) -> str:
    normalized = (
        text.replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )

    normalized = re.sub(
        r"[\"“”‘’]",
        "",
        normalized,
    )

    normalized = re.sub(
        r"[?!。！？,:;]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def contains_latin_text(
    text: str,
) -> bool:
    return bool(
        re.search(
            r"[A-Za-z]",
            text,
        )
    )


def deduplicate_preserving_order(
    values: Iterable[str],
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = (
            normalize_search_text(
                value
            )
        )

        if not normalized:
            continue

        identity = normalized.lower()

        if identity in seen:
            continue

        seen.add(identity)
        result.append(normalized)

    return result


def extract_alias_queries(
    text: str,
) -> list[str]:
    normalized_text = (
        normalize_search_text(
            text
        )
    )

    matches: list[
        tuple[int, int, str]
    ] = []

    for korean_term in ENTITY_ALIASES:
        position = normalized_text.find(
            korean_term
        )

        if position < 0:
            continue

        matches.append(
            (
                position,
                -len(korean_term),
                korean_term,
            )
        )

    matches.sort()

    queries: list[str] = []

    for _, _, korean_term in matches:
        queries.extend(
            ENTITY_ALIASES[
                korean_term
            ]
        )

    return (
        deduplicate_preserving_order(
            queries
        )
    )


def extract_explicit_english_keywords(
    keywords: Sequence[str],
) -> list[str]:
    return (
        deduplicate_preserving_order(
            keyword
            for keyword in keywords
            if contains_latin_text(
                keyword
            )
        )
    )


def translate_known_keywords(
    keywords: Sequence[str],
) -> list[str]:
    queries: list[str] = []

    for keyword in keywords:
        if contains_latin_text(
            keyword
        ):
            queries.append(keyword)
            continue

        queries.extend(
            extract_alias_queries(
                keyword
            )
        )

    return (
        deduplicate_preserving_order(
            queries
        )
    )


def build_base_queries(
    *,
    title: str,
    narration: str,
    keywords: Sequence[str],
) -> list[str]:
    explicit_english = (
        extract_explicit_english_keywords(
            keywords
        )
    )

    if explicit_english:
        return explicit_english

    translated_keywords = (
        translate_known_keywords(
            keywords
        )
    )

    if translated_keywords:
        return translated_keywords

    combined_text = " ".join(
        value
        for value in (
            title,
            narration,
        )
        if value
    )

    alias_queries = (
        extract_alias_queries(
            combined_text
        )
    )

    if alias_queries:
        return alias_queries

    if contains_latin_text(
        combined_text
    ):
        english_parts = re.findall(
            r"[A-Za-z0-9][A-Za-z0-9\s\-']+",
            combined_text,
        )

        normalized_parts = (
            deduplicate_preserving_order(
                english_parts
            )
        )

        if normalized_parts:
            return normalized_parts

    raise SearchPromptError(
        "검색 가능한 영문 키워드를 만들 수 없습니다.\n"
        "Scene의 keywords 또는 media.keywords에 "
        "영문 핵심 키워드를 추가해야 합니다.\n"
        f"title: {title}"
    )


def choose_intents(
    *,
    base_queries: Sequence[str],
) -> tuple[
    SearchIntent,
    ...,
]:
    combined = " ".join(
        base_queries
    ).lower()

    intents: list[SearchIntent] = [
        "primary",
        "wide",
        "detail",
        "atmosphere",
    ]

    aerial_terms = (
        "city",
        "ruins",
        "landscape",
        "desert",
        "island",
        "mountain",
        "cappadocia",
        "pompeii",
    )

    map_terms = (
        "city",
        "country",
        "location",
        "route",
        "turkey",
        "italy",
        "cappadocia",
    )

    if any(
        term in combined
        for term in aerial_terms
    ):
        intents.append(
            "aerial"
        )

    if any(
        term in combined
        for term in map_terms
    ):
        intents.append(
            "map"
        )

    return tuple(
        dict.fromkeys(
            intents
        )
    )


def build_query_variants(
    *,
    base_query: str,
    intent: SearchIntent,
) -> list[str]:
    suffixes = (
        INTENT_SUFFIXES[
            intent
        ]
    )

    if not suffixes:
        return [
            base_query
        ]

    return [
        f"{base_query} {suffix}"
        for suffix in suffixes
    ]


def build_scene_search_prompt(
    *,
    scene_id: str,
    title: str,
    narration: str,
    keywords: Sequence[str],
    max_queries: int = 10,
) -> SceneSearchPrompt:
    if max_queries < 1:
        raise SearchPromptError(
            "max_queries는 1 이상이어야 합니다."
        )

    normalized_title = (
        normalize_search_text(
            title
        )
    )

    normalized_narration = (
        normalize_search_text(
            narration
        )
    )

    normalized_keywords = tuple(
        deduplicate_preserving_order(
            keywords
        )
    )

    base_queries = build_base_queries(
        title=normalized_title,
        narration=normalized_narration,
        keywords=normalized_keywords,
    )

    intents = choose_intents(
        base_queries=base_queries
    )

    query_candidates: list[
        tuple[
            str,
            SearchIntent,
        ]
    ] = []

    # 핵심 검색어를 최우선으로 사용합니다.
    for base_query in base_queries:
        query_candidates.append(
            (
                base_query,
                "primary",
            )
        )

    # 검색어가 너무 많이 늘어나지 않도록
    # 첫 번째와 두 번째 핵심 검색어만 확장합니다.
    expandable_queries = (
        base_queries[:2]
    )

    for intent in intents:
        if intent == "primary":
            continue

        for base_query in expandable_queries:
            for query in (
                build_query_variants(
                    base_query=base_query,
                    intent=intent,
                )
            ):
                query_candidates.append(
                    (
                        query,
                        intent,
                    )
                )

    queries: list[
        SearchQuery
    ] = []

    seen_queries: set[str] = set()

    for raw_query, intent in query_candidates:
        normalized_query = (
            normalize_search_text(
                raw_query
            )
        )

        if not normalized_query:
            continue

        # Wikimedia에는 영문 검색어만 전달합니다.
        if not contains_latin_text(
            normalized_query
        ):
            continue

        identity = (
            normalized_query.lower()
        )

        if identity in seen_queries:
            continue

        seen_queries.add(
            identity
        )

        queries.append(
            SearchQuery(
                query=(
                    normalized_query
                ),
                intent=intent,
                priority=(
                    len(queries) + 1
                ),
            )
        )

        if (
            len(queries)
            >= max_queries
        ):
            break

    if not queries:
        raise SearchPromptError(
            f"{scene_id}: 영문 미디어 검색어가 "
            "생성되지 않았습니다."
        )

    return SceneSearchPrompt(
        scene_id=scene_id,
        title=normalized_title,
        narration=(
            normalized_narration
        ),
        source_keywords=(
            normalized_keywords
        ),
        queries=tuple(
            queries
        ),
    )


def save_search_prompt(
    prompt: SceneSearchPrompt,
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_text(
        json.dumps(
            prompt.to_dict(),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def build_argument_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Director Scene 정보를 이용해 "
            "영문 미디어 검색어를 생성합니다."
        )
    )

    parser.add_argument(
        "--scene-id",
        default="scene_001",
    )

    parser.add_argument(
        "--title",
        default=(
            "땅속에 도시 전체가 "
            "숨겨져 있다면"
        ),
    )

    parser.add_argument(
        "--narration",
        default=(
            "수백 년 동안 아무도 몰랐던 "
            "도시가 땅속에서 발견된다면 "
            "믿으시겠습니까?"
        ),
    )

    parser.add_argument(
        "--keyword",
        action="append",
        default=[],
    )

    parser.add_argument(
        "--max-queries",
        type=int,
        default=10,
    )

    parser.add_argument(
        "--output",
        default=None,
    )

    return parser


def print_prompt(
    prompt: SceneSearchPrompt,
) -> None:
    print("=" * 66)
    print(
        " YouTube Content Factory "
        "Director Search Prompt"
    )
    print("=" * 66)

    print(
        f"{'scene_id':>18}: "
        f"{prompt.scene_id}"
    )

    print(
        f"{'primary':>18}: "
        f"{prompt.primary_query}"
    )

    print("-" * 66)

    for query in prompt.queries:
        print(
            f"[{query.priority:02d}] "
            f"{query.intent:<12} "
            f"{query.query}"
        )

    print("-" * 66)

    print(
        "[성공] 영문 미디어 검색어 생성 완료"
    )


def main(
) -> int:
    parser = build_argument_parser()

    arguments = parser.parse_args()

    try:
        prompt = (
            build_scene_search_prompt(
                scene_id=(
                    arguments.scene_id
                ),
                title=arguments.title,
                narration=(
                    arguments.narration
                ),
                keywords=(
                    arguments.keyword
                ),
                max_queries=(
                    arguments.max_queries
                ),
            )
        )

        if arguments.output:
            save_search_prompt(
                prompt,
                Path(
                    arguments.output
                ),
            )

    except SearchPromptError as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )

        return 1

    print_prompt(
        prompt
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )