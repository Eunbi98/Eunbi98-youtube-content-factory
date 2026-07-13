from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Literal, Sequence


SearchIntent = Literal[
    "primary",
    "portrait",
    "wide",
    "detail",
    "interior",
    "aerial",
    "map",
    "atmosphere",
    "historical",
    "scientific",
    "people",
]

MediaKind = Literal[
    "image",
    "video",
    "any",
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
    media_kind: MediaKind = "any"

    def __post_init__(self) -> None:
        normalized_query = normalize_search_text(self.query)

        if not normalized_query:
            raise SearchPromptError(
                "검색어는 비어 있을 수 없습니다."
            )

        if self.priority < 1:
            raise SearchPromptError(
                "priority는 1 이상이어야 합니다."
            )

        if self.media_kind not in {
            "image",
            "video",
            "any",
        }:
            raise SearchPromptError(
                "지원하지 않는 media_kind입니다: "
                f"{self.media_kind}"
            )

        object.__setattr__(
            self,
            "query",
            normalized_query,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "query": self.query,
            "intent": self.intent,
            "priority": self.priority,
            "mediaKind": self.media_kind,
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
    entities: tuple[str, ...]
    queries: tuple[SearchQuery, ...]

    def __post_init__(self) -> None:
        normalized_scene_id = self.scene_id.strip()

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
    def primary_query(self) -> str:
        return self.queries[0].query

    def to_dict(self) -> dict[str, object]:
        return {
            "sceneId": self.scene_id,
            "title": self.title,
            "narration": self.narration,
            "sourceKeywords": list(
                self.source_keywords
            ),
            "entities": list(self.entities),
            "primaryQuery": self.primary_query,
            "queries": [
                query.to_dict()
                for query in self.queries
            ],
        }


ENTITY_ALIASES: dict[
    str,
    tuple[str, ...],
] = {
    "데린쿠유": (
        "Derinkuyu underground city",
        "Derinkuyu Cappadocia",
        "ancient underground city Turkey",
    ),
    "지하도시": (
        "ancient underground city",
        "underground city tunnels",
        "subterranean settlement",
    ),
    "지하 도시": (
        "ancient underground city",
        "underground city tunnels",
        "subterranean settlement",
    ),
    "땅속 도시": (
        "ancient underground city",
        "subterranean ancient city",
        "underground tunnels",
    ),
    "카파도키아": (
        "Cappadocia Turkey",
        "Cappadocia landscape",
        "Cappadocia underground city",
    ),
    "폼페이": (
        "Pompeii ruins",
        "Pompeii archaeological site",
        "ancient Pompeii city",
    ),
    "타이타닉": (
        "RMS Titanic",
        "Titanic ship",
        "Titanic wreck",
    ),
    "늑대": (
        "gray wolf",
        "wild wolf",
        "wolf pack",
    ),
    "피라미드": (
        "Great Pyramid of Giza",
        "Egypt pyramids",
        "ancient Egyptian pyramid",
    ),
    "화성": (
        "Mars planet",
        "Mars surface",
        "NASA Mars mission",
    ),
    "달": (
        "Moon surface",
        "NASA Moon mission",
        "lunar landscape",
    ),
    "우주": (
        "outer space",
        "deep space",
        "space mission",
    ),
    "우주비행사": (
        "NASA astronaut",
        "astronaut in space",
        "astronaut space station",
    ),
    "국제우주정거장": (
        "International Space Station",
        "ISS orbit",
        "astronaut inside ISS",
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
    "월드컵": (
        "FIFA World Cup",
        "World Cup stadium",
        "international football tournament",
    ),
    "사막": (
        "desert landscape",
        "sand dunes",
        "desert aerial view",
    ),
    "열돔": (
        "heat dome weather",
        "extreme heat map",
        "heat dome diagram",
    ),
    "폭염": (
        "extreme heatwave",
        "heatwave city",
        "global heat map",
    ),
    "열섬": (
        "urban heat island",
        "city heat thermal image",
        "urban heat map",
    ),
    "물고기 비": (
        "fish rain phenomenon",
        "animals falling from sky",
        "fish storm",
    ),
    "토네이도": (
        "tornado storm",
        "tornado landscape",
        "tornado aerial footage",
    ),
    "태풍": (
        "typhoon satellite image",
        "tropical cyclone",
        "hurricane storm",
    ),
    "홍수": (
        "severe flood",
        "flooded city",
        "river flooding",
    ),
    "화산": (
        "volcano eruption",
        "active volcano",
        "lava flow",
    ),
    "지진": (
        "earthquake damage",
        "seismic activity",
        "earthquake fault",
    ),
    "빙하": (
        "glacier",
        "melting glacier",
        "polar ice aerial view",
    ),
    "북극": (
        "Arctic landscape",
        "Arctic sea ice",
        "North Pole",
    ),
    "남극": (
        "Antarctica landscape",
        "Antarctic ice",
        "South Pole research station",
    ),
    "심해": (
        "deep sea",
        "deep ocean",
        "deep sea exploration",
    ),
    "블랙홀": (
        "black hole",
        "black hole visualization",
        "event horizon telescope",
    ),
    "은하": (
        "galaxy",
        "Milky Way galaxy",
        "deep space galaxy",
    ),
    "운석": (
        "meteorite",
        "meteor impact",
        "asteroid entering atmosphere",
    ),
    "소행성": (
        "asteroid",
        "NASA asteroid mission",
        "asteroid in space",
    ),
    "고대 도시": (
        "ancient city ruins",
        "archaeological site",
        "lost ancient city",
    ),
    "유적": (
        "ancient ruins",
        "archaeological ruins",
        "historical site",
    ),
    "고고학": (
        "archaeological excavation",
        "archaeologist excavation",
        "ancient artifact discovery",
    ),
    "미라": (
        "ancient Egyptian mummy",
        "mummy museum",
        "Egyptian archaeology",
    ),
    "이집트": (
        "ancient Egypt",
        "Egypt archaeological site",
        "Egypt desert landscape",
    ),
    "로마": (
        "ancient Rome",
        "Roman ruins",
        "Roman Empire archaeology",
    ),
    "바이킹": (
        "Viking ship",
        "Viking archaeology",
        "Norse history",
    ),
    "공룡": (
        "dinosaur fossil",
        "dinosaur museum",
        "paleontology excavation",
    ),
    "화석": (
        "fossil",
        "fossil excavation",
        "natural history museum fossil",
    ),
    "해저 도시": (
        "underwater ancient city",
        "submerged ruins",
        "underwater archaeology",
    ),
    "난파선": (
        "shipwreck underwater",
        "sunken ship",
        "underwater shipwreck",
    ),
    "동굴": (
        "cave interior",
        "underground cave",
        "limestone cave",
    ),
    "정글": (
        "tropical jungle",
        "rainforest aerial view",
        "dense jungle",
    ),
    "아마존": (
        "Amazon rainforest",
        "Amazon river aerial view",
        "Amazon jungle",
    ),
    "에베레스트": (
        "Mount Everest",
        "Everest summit",
        "Himalaya mountains",
    ),
    "히말라야": (
        "Himalaya mountains",
        "Himalayan landscape",
        "snow mountain aerial view",
    ),
    "번개": (
        "lightning storm",
        "lightning strike",
        "thunderstorm",
    ),
    "오로라": (
        "aurora borealis",
        "northern lights",
        "aurora night sky",
    ),
    "바다": (
        "ocean",
        "open sea",
        "ocean aerial view",
    ),
    "고래": (
        "whale underwater",
        "humpback whale",
        "whale ocean",
    ),
    "상어": (
        "shark underwater",
        "great white shark",
        "shark ocean",
    ),
    "문어": (
        "octopus underwater",
        "giant octopus",
        "octopus close up",
    ),
    "개미": (
        "ant colony",
        "ants macro",
        "ant nest",
    ),
    "벌": (
        "honey bee",
        "bee colony",
        "beehive close up",
    ),
    "문명": (
        "ancient civilization",
        "lost civilization",
        "archaeological civilization",
    ),
    "미스터리": (
        "historical mystery",
        "unexplained phenomenon",
        "mysterious ancient site",
    ),
}


ENGLISH_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "has",
    "have",
    "how",
    "in",
    "into",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "their",
    "this",
    "to",
    "was",
    "were",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
    "would",
}


INTENT_SUFFIXES: dict[
    SearchIntent,
    tuple[str, ...],
] = {
    "primary": (),
    "portrait": (
        "vertical",
        "portrait view",
    ),
    "wide": (
        "wide view",
        "landscape",
    ),
    "detail": (
        "close up",
        "detailed view",
    ),
    "interior": (
        "interior",
        "inside",
    ),
    "aerial": (
        "aerial view",
        "drone view",
    ),
    "map": (
        "map",
        "location map",
    ),
    "atmosphere": (
        "cinematic",
        "dramatic",
    ),
    "historical": (
        "historical photograph",
        "archive",
    ),
    "scientific": (
        "scientific visualization",
        "diagram",
    ),
    "people": (
        "people",
        "documentary",
    ),
}


AERIAL_TERMS = {
    "city",
    "ruins",
    "landscape",
    "desert",
    "island",
    "mountain",
    "cappadocia",
    "pompeii",
    "forest",
    "rainforest",
    "river",
    "ocean",
    "glacier",
    "volcano",
    "stadium",
}


MAP_TERMS = {
    "city",
    "country",
    "location",
    "route",
    "turkey",
    "italy",
    "egypt",
    "rome",
    "cappadocia",
    "pompeii",
    "ocean",
    "island",
    "mountain",
}


HISTORICAL_TERMS = {
    "ancient",
    "history",
    "historical",
    "archaeology",
    "archaeological",
    "ruins",
    "civilization",
    "empire",
    "titanic",
    "viking",
    "roman",
    "egyptian",
    "mummy",
    "artifact",
}


SCIENTIFIC_TERMS = {
    "nasa",
    "space",
    "mars",
    "moon",
    "planet",
    "galaxy",
    "black hole",
    "asteroid",
    "meteor",
    "weather",
    "heat",
    "earthquake",
    "volcano",
    "storm",
    "glacier",
    "ocean",
    "scientific",
}


PEOPLE_TERMS = {
    "astronaut",
    "archaeologist",
    "scientist",
    "explorer",
    "people",
    "worker",
    "researcher",
}


def normalize_search_text(text: str) -> str:
    if not isinstance(text, str):
        return ""

    normalized = unicodedata.normalize(
        "NFKC",
        text,
    )

    normalized = (
        normalized
        .replace("\r", " ")
        .replace("\n", " ")
        .strip()
    )

    normalized = re.sub(
        r"[\"“”‘’`]",
        "",
        normalized,
    )

    normalized = re.sub(
        r"[?!。！？,:;|/\\]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"[()\[\]{}<>]+",
        " ",
        normalized,
    )

    normalized = re.sub(
        r"\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def contains_latin_text(text: str) -> bool:
    return bool(
        re.search(
            r"[A-Za-z]",
            text,
        )
    )


def contains_korean_text(text: str) -> bool:
    return bool(
        re.search(
            r"[가-힣]",
            text,
        )
    )


def deduplicate_preserving_order(
    values: Iterable[str],
) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()

    for value in values:
        normalized = normalize_search_text(
            value
        )

        if not normalized:
            continue

        identity = normalized.casefold()

        if identity in seen:
            continue

        seen.add(identity)
        result.append(normalized)

    return result


def tokenize_english_text(
    text: str,
) -> list[str]:
    tokens = re.findall(
        r"[A-Za-z][A-Za-z0-9'-]*",
        text,
    )

    return [
        token
        for token in tokens
        if (
            len(token) >= 2
            and token.casefold()
            not in ENGLISH_STOPWORDS
        )
    ]


def extract_english_phrases(
    text: str,
) -> list[str]:
    normalized = normalize_search_text(
        text
    )

    raw_phrases = re.findall(
        r"[A-Za-z0-9]"
        r"[A-Za-z0-9'&+\- ]{1,80}",
        normalized,
    )

    phrases: list[str] = []

    for raw_phrase in raw_phrases:
        tokens = tokenize_english_text(
            raw_phrase
        )

        if not tokens:
            continue

        phrase = " ".join(
            tokens[:8]
        )

        if phrase:
            phrases.append(phrase)

    return deduplicate_preserving_order(
        phrases
    )


def extract_alias_matches(
    text: str,
) -> list[
    tuple[int, int, str]
]:
    normalized_text = normalize_search_text(
        text
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

    return matches


def extract_alias_queries(
    text: str,
) -> list[str]:
    queries: list[str] = []

    for _, _, korean_term in (
        extract_alias_matches(text)
    ):
        queries.extend(
            ENTITY_ALIASES[korean_term]
        )

    return deduplicate_preserving_order(
        queries
    )


def extract_detected_entities(
    text: str,
) -> list[str]:
    entities = [
        korean_term
        for _, _, korean_term in (
            extract_alias_matches(text)
        )
    ]

    entities.extend(
        extract_english_phrases(text)
    )

    return deduplicate_preserving_order(
        entities
    )


def extract_explicit_english_keywords(
    keywords: Sequence[str],
) -> list[str]:
    queries: list[str] = []

    for keyword in keywords:
        if not contains_latin_text(
            keyword
        ):
            continue

        phrases = extract_english_phrases(
            keyword
        )

        if phrases:
            queries.extend(phrases)
        else:
            queries.append(keyword)

    return deduplicate_preserving_order(
        queries
    )


def translate_known_keywords(
    keywords: Sequence[str],
) -> list[str]:
    queries: list[str] = []

    for keyword in keywords:
        normalized = normalize_search_text(
            keyword
        )

        if not normalized:
            continue

        if contains_latin_text(
            normalized
        ):
            queries.extend(
                extract_english_phrases(
                    normalized
                )
            )
            continue

        queries.extend(
            extract_alias_queries(
                normalized
            )
        )

    return deduplicate_preserving_order(
        queries
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

    translated_keywords = (
        translate_known_keywords(
            keywords
        )
    )

    combined_text = " ".join(
        value
        for value in (
            title,
            narration,
        )
        if value
    )

    alias_queries = extract_alias_queries(
        combined_text
    )

    english_phrases = (
        extract_english_phrases(
            combined_text
        )
    )

    candidates = (
        explicit_english
        + translated_keywords
        + alias_queries
        + english_phrases
    )

    queries = deduplicate_preserving_order(
        candidates
    )

    if queries:
        return queries

    raise SearchPromptError(
        "검색 가능한 영문 키워드를 만들 수 없습니다.\n"
        "Scene의 keywords, media.keywords 또는 "
        "mediaSearch.sourceKeywords에 영문 핵심 "
        "키워드를 추가해야 합니다.\n"
        f"title: {title}"
    )


def choose_intents(
    *,
    base_queries: Sequence[str],
) -> tuple[SearchIntent, ...]:
    combined = " ".join(
        base_queries
    ).casefold()

    intents: list[SearchIntent] = [
        "primary",
        "wide",
        "detail",
        "atmosphere",
    ]

    if any(
        term in combined
        for term in AERIAL_TERMS
    ):
        intents.append("aerial")

    if any(
        term in combined
        for term in MAP_TERMS
    ):
        intents.append("map")

    if any(
        term in combined
        for term in HISTORICAL_TERMS
    ):
        intents.append("historical")

    if any(
        term in combined
        for term in SCIENTIFIC_TERMS
    ):
        intents.append("scientific")

    if any(
        term in combined
        for term in PEOPLE_TERMS
    ):
        intents.append("people")

    return tuple(
        dict.fromkeys(intents)
    )


def infer_media_kind(
    *,
    intent: SearchIntent,
) -> MediaKind:
    if intent in {
        "map",
        "historical",
        "scientific",
    }:
        return "image"

    if intent in {
        "primary",
        "portrait",
        "wide",
        "detail",
        "interior",
        "aerial",
        "atmosphere",
        "people",
    }:
        return "any"

    return "any"


VISUAL_SUFFIX_PATTERNS: tuple[
    tuple[SearchIntent, re.Pattern[str]],
    ...,
] = (
    (
        "portrait",
        re.compile(
            r"\\b(?:vertical|portrait view)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "wide",
        re.compile(
            r"\\b(?:wide view|landscape)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "detail",
        re.compile(
            r"\\b(?:close up|detailed view)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "interior",
        re.compile(
            r"\\b(?:interior|inside)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "aerial",
        re.compile(
            r"\\b(?:aerial view|drone view)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "map",
        re.compile(
            r"\\b(?:location map|map)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "atmosphere",
        re.compile(
            r"\\b(?:cinematic|dramatic)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "historical",
        re.compile(
            r"\\b(?:historical photograph|archive)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "scientific",
        re.compile(
            r"\\b(?:scientific visualization|diagram)\\b",
            flags=re.IGNORECASE,
        ),
    ),
    (
        "people",
        re.compile(
            r"\\b(?:people|documentary)\\b",
            flags=re.IGNORECASE,
        ),
    ),
)


def detect_query_intent(
    query: str,
) -> SearchIntent:
    normalized = normalize_search_text(
        query
    )

    for intent, pattern in (
        VISUAL_SUFFIX_PATTERNS
    ):
        if pattern.search(normalized):
            return intent

    return "primary"


def strip_visual_suffixes(
    query: str,
) -> str:
    normalized = normalize_search_text(
        query
    )

    for _, pattern in (
        VISUAL_SUFFIX_PATTERNS
    ):
        normalized = pattern.sub(
            " ",
            normalized,
        )

    normalized = re.sub(
        r"\\s+",
        " ",
        normalized,
    )

    return normalized.strip()


def has_intent_suffix(
    *,
    query: str,
    intent: SearchIntent,
) -> bool:
    normalized = normalize_search_text(
        query
    )

    for candidate_intent, pattern in (
        VISUAL_SUFFIX_PATTERNS
    ):
        if (
            candidate_intent == intent
            and pattern.search(normalized)
        ):
            return True

    return False


def build_query_variants(
    *,
    base_query: str,
    intent: SearchIntent,
) -> list[str]:
    normalized_base = normalize_search_text(
        base_query
    )

    if not normalized_base:
        return []

    if intent == "primary":
        return [
            strip_visual_suffixes(
                normalized_base
            )
        ]

    if has_intent_suffix(
        query=normalized_base,
        intent=intent,
    ):
        return [normalized_base]

    clean_base = strip_visual_suffixes(
        normalized_base
    )

    if not clean_base:
        return []

    return [
        normalize_search_text(
            f"{clean_base} {suffix}"
        )
        for suffix in INTENT_SUFFIXES[
            intent
        ]
    ]


def calculate_query_quality(
    query: str,
) -> float:
    normalized = normalize_search_text(
        query
    )

    tokens = tokenize_english_text(
        normalized
    )

    if not tokens:
        return 0.0

    score = 0.0
    score += min(
        len(tokens),
        6,
    ) * 4.0

    if 2 <= len(tokens) <= 6:
        score += 10.0

    if contains_korean_text(
        normalized
    ):
        score -= 20.0

    if len(normalized) > 80:
        score -= 8.0

    if re.search(
        r"\b("
        r"image|photo|picture|footage"
        r")\b",
        normalized,
        flags=re.IGNORECASE,
    ):
        score -= 3.0

    return round(
        score,
        3,
    )


def rank_base_queries(
    queries: Sequence[str],
) -> list[str]:
    indexed_queries = list(
        enumerate(queries)
    )

    ranked = sorted(
        indexed_queries,
        key=lambda item: (
            -calculate_query_quality(
                item[1]
            ),
            item[0],
        ),
    )

    return [
        query
        for _, query in ranked
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

    if max_queries > 30:
        raise SearchPromptError(
            "max_queries는 30 이하여야 합니다."
        )

    normalized_scene_id = (
        normalize_search_text(scene_id)
    )

    normalized_title = (
        normalize_search_text(title)
    )

    normalized_narration = (
        normalize_search_text(narration)
    )

    normalized_keywords = tuple(
        deduplicate_preserving_order(
            keywords
        )
    )

    combined_text = " ".join(
        value
        for value in (
            normalized_title,
            normalized_narration,
            *normalized_keywords,
        )
        if value
    )

    entities = tuple(
        extract_detected_entities(
            combined_text
        )
    )

    raw_base_queries = rank_base_queries(
        build_base_queries(
            title=normalized_title,
            narration=normalized_narration,
            keywords=normalized_keywords,
        )
    )

    canonical_base_queries = (
        deduplicate_preserving_order(
            strip_visual_suffixes(query)
            for query in raw_base_queries
        )
    )

    canonical_base_queries = [
        query
        for query in canonical_base_queries
        if query
    ]

    if not canonical_base_queries:
        raise SearchPromptError(
            f"{normalized_scene_id}: "
            "기본 검색어를 생성하지 못했습니다."
        )

    intents = choose_intents(
        base_queries=canonical_base_queries
    )

    query_candidates: list[
        tuple[
            str,
            SearchIntent,
            MediaKind,
        ]
    ] = []

    for base_query in (
        canonical_base_queries[:2]
    ):
        query_candidates.append(
            (
                base_query,
                "primary",
                "any",
            )
        )

    for raw_query in raw_base_queries:
        detected_intent = (
            detect_query_intent(
                raw_query
            )
        )

        if detected_intent == "primary":
            continue

        query_candidates.append(
            (
                raw_query,
                detected_intent,
                infer_media_kind(
                    intent=detected_intent
                ),
            )
        )

    expandable_queries = (
        canonical_base_queries[:2]
    )

    for intent in intents:
        if intent == "primary":
            continue

        media_kind = infer_media_kind(
            intent=intent
        )

        for base_query in (
            expandable_queries
        ):
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
                        media_kind,
                    )
                )

    queries: list[SearchQuery] = []
    seen_queries: set[str] = set()

    for (
        raw_query,
        intent,
        media_kind,
    ) in query_candidates:
        normalized_query = (
            normalize_search_text(
                raw_query
            )
        )

        if not normalized_query:
            continue

        if not contains_latin_text(
            normalized_query
        ):
            continue

        identity = (
            normalized_query.casefold()
        )

        if identity in seen_queries:
            continue

        seen_queries.add(identity)

        queries.append(
            SearchQuery(
                query=normalized_query,
                intent=intent,
                priority=(
                    len(queries) + 1
                ),
                media_kind=media_kind,
            )
        )

        if len(queries) >= max_queries:
            break

    if not queries:
        raise SearchPromptError(
            f"{normalized_scene_id}: "
            "영문 미디어 검색어가 "
            "생성되지 않았습니다."
        )

    return SceneSearchPrompt(
        scene_id=normalized_scene_id,
        title=normalized_title,
        narration=normalized_narration,
        source_keywords=(
            normalized_keywords
        ),
        entities=entities,
        queries=tuple(queries),
    )


def save_search_prompt(
    prompt: SceneSearchPrompt,
    output_path: Path,
) -> None:
    resolved_path = (
        output_path.resolve()
    )

    resolved_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = (
        resolved_path.with_suffix(
            f"{resolved_path.suffix}.tmp"
        )
    )

    payload = json.dumps(
        prompt.to_dict(),
        ensure_ascii=False,
        indent=2,
    ) + "\n"

    try:
        temporary_path.write_text(
            payload,
            encoding="utf-8",
        )

        temporary_path.replace(
            resolved_path
        )
    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink()

        raise SearchPromptError(
            "검색 프롬프트 저장에 실패했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc


def build_argument_parser() -> (
    argparse.ArgumentParser
):
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
    print("=" * 72)
    print(
        " YouTube Content Factory "
        "Scene Query Generator"
    )
    print("=" * 72)

    print(
        f"{'scene_id':>18}: "
        f"{prompt.scene_id}"
    )

    print(
        f"{'primary':>18}: "
        f"{prompt.primary_query}"
    )

    print(
        f"{'entities':>18}: "
        f"{', '.join(prompt.entities) or '없음'}"
    )

    print("-" * 72)

    for query in prompt.queries:
        print(
            f"[{query.priority:02d}] "
            f"{query.intent:<12} "
            f"{query.media_kind:<6} "
            f"{query.query}"
        )

    print("-" * 72)
    print(
        "[성공] 영문 미디어 검색어 생성 완료"
    )


def main() -> int:
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
                Path(arguments.output),
            )

    except SearchPromptError as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )
        return 1

    print_prompt(prompt)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())