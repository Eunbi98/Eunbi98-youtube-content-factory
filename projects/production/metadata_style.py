from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any, Iterable


UPLOAD_TAGS = ("쇼츠", "shorts")
DESCRIPTION_CTA = "댓글로 여러분의 생각을 남겨주세요!"


METADATA_STYLE_INSTRUCTIONS = (
    "Follow the channel's established Korean upload-copy style. The YouTube "
    "title must be newly rewritten as a concise curiosity hook, not copied or "
    "lightly edited from selectedTopic.topic, a news headline, or an evidence "
    "title. Prefer a natural question such as '왜 ...일까?' or an intriguing "
    "statement such as '500년째 아무도 읽지 못한 책, 보이니치 문서'. Do "
    "not use press-release wording, outlet names, or a news-headline list of "
    "who announced or discovered what. Keep the title hook to 42 Korean "
    "characters or fewer. Never put hashtags in episode.title or metadata.title. "
    "Keep '쇼츠' and 'shorts' only in metadata.tags as upload tags. The description "
    "must use short Korean paragraphs separated by blank lines in this order: "
    "a conversational opening question, verified core facts, an interesting "
    "meaning or limitation, a viewer question, and the exact final sentence "
    "'댓글로 여러분의 생각을 남겨주세요!'. The pinned comment must not read "
    "like a summary or news report. Ask one easy-to-answer question about the "
    "video, add one short conversational reaction when natural, and finish "
    "with a sentence that asks viewers to share their thoughts, experience, "
    "or guess in the comments. Preserve factual accuracy and uncertainty."
)


class MetadataStyleError(ValueError):
    """업로드 문안이 채널의 제목·설명·댓글 스타일을 따르지 않음."""


def strip_title_hashtags(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"(?:^|\s)#[^\s#]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_upload_metadata(metadata: dict[str, Any]) -> None:
    metadata["title"] = strip_title_hashtags(metadata.get("title"))
    raw_tags = metadata.get("tags")
    tags: list[str] = []
    if isinstance(raw_tags, list):
        for raw_tag in raw_tags:
            if not isinstance(raw_tag, str):
                continue
            tag = raw_tag.lstrip("#").strip()
            if tag and tag.lower() not in {item.lower() for item in tags}:
                tags.append(tag)
    for required_tag in UPLOAD_TAGS:
        if required_tag.lower() not in {item.lower() for item in tags}:
            tags.append(required_tag)
    metadata["tags"] = tags


def validate_metadata_style(
    metadata: dict[str, Any],
    *,
    reference_titles: Iterable[str] = (),
) -> None:
    title = _required_text(metadata, "title")
    description = _required_text(metadata, "description")
    pinned_comment = _required_text(metadata, "pinnedComment")

    if "#" in title:
        raise MetadataStyleError(
            "metadata.title에는 해시태그를 넣을 수 없습니다. "
            "#쇼츠와 #shorts는 metadata.tags에서만 사용해야 합니다."
        )
    if len(title) > 42:
        raise MetadataStyleError(
            "metadata.title의 호기심형 문장은 42자 이하여야 합니다."
        )
    if "\n" in title:
        raise MetadataStyleError("metadata.title에는 줄바꿈을 넣을 수 없습니다.")

    tags = metadata.get("tags")
    normalized_tags = {
        str(tag).lstrip("#").strip().lower()
        for tag in tags
        if isinstance(tag, str) and tag.strip()
    } if isinstance(tags, list) else set()
    missing_upload_tags = {
        tag for tag in UPLOAD_TAGS if tag.lower() not in normalized_tags
    }
    if missing_upload_tags:
        raise MetadataStyleError(
            "metadata.tags에는 업로드용 '쇼츠'와 'shorts'가 필요합니다."
        )

    normalized_hook = _normalize_title(title)
    for reference_title in reference_titles:
        normalized_reference = _normalize_title(reference_title)
        if not normalized_reference:
            continue
        similarity = SequenceMatcher(
            None,
            normalized_hook,
            normalized_reference,
        ).ratio()
        if normalized_hook == normalized_reference or similarity >= 0.88:
            raise MetadataStyleError(
                "metadata.title이 기사 또는 선택 주제 제목과 너무 유사합니다. "
                "채널 스타일의 호기심형 제목으로 다시 작성해야 합니다."
            )

    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(r"\n\s*\n", description)
        if paragraph.strip()
    ]
    if len(paragraphs) < 4:
        raise MetadataStyleError(
            "metadata.description은 빈 줄로 구분된 문단이 최소 4개 필요합니다."
        )
    if "?" not in paragraphs[0]:
        raise MetadataStyleError(
            "metadata.description의 첫 문단은 시청자에게 묻는 질문이어야 합니다."
        )
    if paragraphs[-1] != DESCRIPTION_CTA:
        raise MetadataStyleError(
            f"metadata.description은 '{DESCRIPTION_CTA}'로 끝나야 합니다."
        )
    if "?" not in description[:-len(DESCRIPTION_CTA)]:
        raise MetadataStyleError(
            "metadata.description에 영상 내용과 연결된 시청자 질문이 필요합니다."
        )

    if "?" not in pinned_comment:
        raise MetadataStyleError(
            "metadata.pinnedComment에는 답하기 쉬운 질문이 필요합니다."
        )
    if "댓글" not in pinned_comment:
        raise MetadataStyleError(
            "metadata.pinnedComment에는 댓글 참여 유도 문장이 필요합니다."
        )


def collect_reference_titles(
    job_payload: dict[str, Any],
    evidence_payload: dict[str, Any],
) -> list[str]:
    titles: list[str] = []
    selected_topic = job_payload.get("selectedTopic")
    if isinstance(selected_topic, dict):
        _append_text(titles, selected_topic.get("topic"))
        sources = selected_topic.get("sources")
        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, dict):
                    _append_text(titles, source.get("title"))

    items = evidence_payload.get("items")
    if isinstance(items, list):
        for item in items:
            if isinstance(item, dict):
                _append_text(titles, item.get("title"))
    return titles


def _required_text(metadata: dict[str, Any], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value.strip():
        raise MetadataStyleError(f"metadata.{key}가 필요합니다.")
    return value.strip()


def _normalize_title(value: object) -> str:
    text = str(value or "")
    text = re.sub(r"#쇼츠|#shorts", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+-\s+[^-]+$", "", text)
    return re.sub(r"[^0-9a-z가-힣]", "", text.lower())


def _append_text(target: list[str], value: object) -> None:
    text = str(value or "").strip()
    if text and text not in target:
        target.append(text)
