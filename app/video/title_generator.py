from __future__ import annotations

import re

from app.story.text_normalizer import normalize_english_terms


class VideoTitleGenerator:
    def generate(self, article) -> str:
        script = normalize_english_terms(getattr(article, "script", ""))
        script_hook = self._first_script_line(getattr(article, "script", ""))
        thumbnail = normalize_english_terms(getattr(article, "thumbnail", ""))

        if "이상한 신호" in script:
            return "우주에서 발견된 이상한 신호"

        if script_hook:
            return self._title_from_hook(script_hook)

        if self._is_usable_korean_title(thumbnail):
            return self._clean_title(thumbnail)

        return "오늘의 핵심 뉴스"

    def _title_from_hook(self, hook: str) -> str:
        hook = normalize_english_terms(hook)
        hook = self._clean_title(hook)

        replacements = {
            "과학자들이 하늘에서 이상한 신호를 포착했습니다": "우주에서 발견된 이상한 신호",
            "이 기술이 정말 우리의 생활을 바꿀 수 있을까요": "일상을 바꿀 새로운 기술",
            "사람들이 이 동물의 행동에 마음을 빼앗긴 이유가 있습니다": "사람들을 움직인 동물 이야기",
        }

        for source, title in replacements.items():
            if source in hook:
                return title

        if "이상한 신호" in hook:
            return "우주에서 발견된 이상한 신호"

        hook = re.sub(r"(습니다|습니까|했다|합니다|입니다)[.?!]?$", "", hook)
        hook = hook.strip(" .?!")

        if len(hook) > 18:
            hook = hook[:18].rstrip()

        return hook or "오늘의 핵심 뉴스"

    def _first_script_line(self, script: str) -> str:
        for line in str(script or "").splitlines():
            line = line.strip()

            if line:
                return line

        return ""

    def _is_usable_korean_title(self, title: str) -> bool:
        if not title:
            return False

        korean_chars = len(re.findall(r"[가-힣]", title))
        english_chars = len(re.findall(r"[A-Za-z]", title))

        return korean_chars >= 4 and english_chars == 0

    def _clean_title(self, title: str) -> str:
        title = normalize_english_terms(title)
        title = re.sub(r"\s+", " ", title)
        return title.strip(" .?!")
