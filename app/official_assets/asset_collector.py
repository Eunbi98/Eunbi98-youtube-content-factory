from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from app.official_assets.asset_types import (
    MEDIA_TYPES,
    SOURCE_PRIORITY,
    TRUST_SCORE_BY_SOURCE,
    AssetCandidate,
)


class OfficialAssetCollector:
    def __init__(
        self,
        *,
        min_candidates_per_scene: int = 3,
        candidates_per_scene: int = 12,
        enable_live_lookup: bool = False,
        request_timeout_seconds: float = 8,
    ) -> None:
        self.min_candidates_per_scene = min_candidates_per_scene
        self.candidates_per_scene = candidates_per_scene
        self.enable_live_lookup = enable_live_lookup
        self.request_timeout_seconds = request_timeout_seconds

    def generate_from_files(
        self,
        knowledge_pack_path: Path | str,
        story_beats_path: Path | str,
        script_path: Path | str,
        output_dir: Path | str | None = None,
    ) -> dict[str, object]:
        knowledge_pack_file = Path(knowledge_pack_path)
        story_beats_file = Path(story_beats_path)
        script_file = Path(script_path)
        target_dir = Path(output_dir) if output_dir else script_file.parent

        knowledge_pack = self._load_json(knowledge_pack_file)
        story_beats = self._load_json(story_beats_file)
        script = self._load_json(script_file)
        episode_id = self._episode_id(knowledge_pack, script, target_dir)

        candidates = self.generate(
            episode_id=episode_id,
            knowledge_pack=knowledge_pack,
            story_beats=story_beats,
            script=script,
        )

        target_dir.mkdir(parents=True, exist_ok=True)
        json_path = target_dir / "asset_candidates.json"
        markdown_path = target_dir / "asset_candidates.md"

        json_path.write_text(
            json.dumps(candidates, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(
            self._render_markdown(candidates),
            encoding="utf-8",
        )

        return candidates

    def generate(
        self,
        *,
        episode_id: str,
        knowledge_pack: dict[str, Any],
        story_beats: dict[str, Any],
        script: dict[str, Any],
    ) -> dict[str, object]:
        narration_lines = self._narration_lines(script, story_beats)
        global_keywords = self._global_keywords(knowledge_pack, story_beats, script)

        result: dict[str, object] = {
            "episode": self._episode_number(episode_id),
            "episode_id": episode_id,
            "source_priority": SOURCE_PRIORITY,
            "trust_score_criteria": TRUST_SCORE_BY_SOURCE,
            "download_policy": "candidates_only_no_download",
        }

        for index, narration in enumerate(narration_lines, start=1):
            scene_key = f"scene_{index:02d}"
            scene_keywords = self._scene_keywords(narration, global_keywords, index)
            scene_candidates = self._collect_scene_candidates(scene_keywords)
            result[scene_key] = [candidate.to_dict() for candidate in scene_candidates]

        return result

    def _collect_scene_candidates(self, keywords: list[str]) -> list[AssetCandidate]:
        candidates: list[AssetCandidate] = []

        if self.enable_live_lookup:
            candidates.extend(self._live_candidates("NASA", keywords))
            candidates.extend(self._live_candidates("Wikimedia Commons", keywords))

        candidates.extend(self._template_candidates(keywords))

        deduped: list[AssetCandidate] = []
        seen: set[tuple[str, str, str]] = set()
        for candidate in candidates:
            key = (candidate.source, candidate.media_type, candidate.url)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(candidate)
            if len(deduped) >= self.candidates_per_scene:
                break

        if len(deduped) < self.min_candidates_per_scene:
            raise ValueError("Each scene must have at least 3 asset candidates.")

        return deduped

    def _template_candidates(self, keywords: list[str]) -> list[AssetCandidate]:
        candidates: list[AssetCandidate] = []
        query = " ".join(keywords[:4])

        for source in SOURCE_PRIORITY:
            for media_type in MEDIA_TYPES:
                candidates.append(
                    AssetCandidate(
                        title=self._candidate_title(source, media_type, query),
                        source=source,
                        url=self._search_url(source, media_type, query),
                        license=self._license_for(source),
                        media_type=media_type,
                        keywords=keywords[:4],
                        trust_score=TRUST_SCORE_BY_SOURCE[source],
                    )
                )

        return candidates

    def _live_candidates(self, source: str, keywords: list[str]) -> list[AssetCandidate]:
        if source == "NASA":
            return self._nasa_live_candidates(keywords)
        if source == "Wikimedia Commons":
            return self._wikimedia_live_candidates(keywords)
        return []

    def _nasa_live_candidates(self, keywords: list[str]) -> list[AssetCandidate]:
        query = " ".join(keywords[:4])
        url = (
            "https://images-api.nasa.gov/search?"
            + urllib.parse.urlencode({"q": query, "media_type": "image,video"})
        )
        payload = self._fetch_json(url)
        items = payload.get("collection", {}).get("items", []) if isinstance(payload, dict) else []
        candidates: list[AssetCandidate] = []

        for item in items[:8]:
            data_items = item.get("data", [])
            if not data_items:
                continue
            data = data_items[0]
            media_type = data.get("media_type")
            if media_type not in MEDIA_TYPES:
                continue
            candidates.append(
                AssetCandidate(
                    title=data.get("title") or f"NASA {media_type} result",
                    source="NASA",
                    url=item.get("href") or url,
                    license="NASA public domain or official media usage terms; verify per asset.",
                    media_type=media_type,
                    keywords=keywords[:4],
                    trust_score=TRUST_SCORE_BY_SOURCE["NASA"],
                )
            )

        return candidates

    def _wikimedia_live_candidates(self, keywords: list[str]) -> list[AssetCandidate]:
        query = " ".join(keywords[:4])
        url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
            {
                "action": "query",
                "generator": "search",
                "gsrsearch": query,
                "gsrnamespace": 6,
                "gsrlimit": 8,
                "prop": "imageinfo",
                "iiprop": "url|extmetadata|mime",
                "format": "json",
            }
        )
        payload = self._fetch_json(url)
        pages = payload.get("query", {}).get("pages", {}) if isinstance(payload, dict) else {}
        candidates: list[AssetCandidate] = []

        for page in pages.values():
            image_info = (page.get("imageinfo") or [{}])[0]
            mime = image_info.get("mime", "")
            media_type = "video" if str(mime).startswith("video/") else "image"
            metadata = image_info.get("extmetadata", {})
            license_value = metadata.get("LicenseShortName", {}).get("value") or "Wikimedia Commons license; verify per asset."
            candidates.append(
                AssetCandidate(
                    title=page.get("title") or f"Wikimedia {media_type} result",
                    source="Wikimedia Commons",
                    url=image_info.get("descriptionurl") or image_info.get("url") or url,
                    license=license_value,
                    media_type=media_type,
                    keywords=keywords[:4],
                    trust_score=TRUST_SCORE_BY_SOURCE["Wikimedia Commons"],
                )
            )

        return candidates

    def _fetch_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "youtube-content-factory/official-asset-collector"},
        )
        with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _global_keywords(
        self,
        knowledge_pack: dict[str, Any],
        story_beats: dict[str, Any],
        script: dict[str, Any],
    ) -> list[str]:
        text = " ".join(
            [
                self._flatten_text(knowledge_pack),
                self._flatten_text(story_beats),
                self._flatten_text(script),
            ]
        )
        keywords = self._domain_expansions(text)
        keywords.extend(self._keyword_candidates(text))
        keywords = self._unique_keywords(keywords)
        if keywords:
            return keywords[:16]
        return ["science", "official", "research", "documentary"]

    def _scene_keywords(
        self,
        narration: str,
        global_keywords: list[str],
        scene_index: int,
    ) -> list[str]:
        local_keywords = self._domain_expansions(narration)
        local_keywords.extend(self._keyword_candidates(narration))
        keywords = self._unique_keywords(local_keywords + global_keywords)

        if len(keywords) < 3:
            keywords.extend(global_keywords[: 3 - len(keywords)])

        if scene_index == 1 and "hook" not in keywords:
            keywords.append("hook")

        return self._unique_keywords(keywords)[:6]

    def _keyword_candidates(self, text: str) -> list[str]:
        normalized = text.replace("_", " ").replace("-", " ")
        words = [
            word.lower()
            for word in re.findall(r"[A-Za-z][A-Za-z0-9]{2,}", normalized)
            if word.lower() not in self._stop_words()
        ]
        phrases: list[str] = []

        for size in (3, 2):
            for index in range(0, max(0, len(words) - size + 1)):
                phrase_words = words[index : index + size]
                if any(word in self._high_signal_words() for word in phrase_words):
                    phrases.append(" ".join(phrase_words))

        return self._unique_keywords(phrases + words)

    def _domain_expansions(self, text: str) -> list[str]:
        lowered = text.lower()
        expansions: list[str] = []
        rules = [
            (("space", "nasa", "iss", "astronaut", "microgravity", "mars"), ["space", "astronaut", "international space station", "microgravity"]),
            (("ocean", "mariana", "trench", "underwater", "submarine", "noaa"), ["deep ocean", "mariana trench", "underwater", "submarine"]),
            (("weather", "storm", "hurricane", "typhoon", "climate"), ["weather", "storm", "satellite imagery", "climate"]),
            (("earth", "planet", "orbit", "satellite"), ["earth", "satellite", "orbit", "planet"]),
            (("volcano", "earthquake", "geology"), ["geology", "volcano", "earthquake", "natural hazard"]),
        ]
        for triggers, values in rules:
            if any(trigger in lowered for trigger in triggers):
                expansions.extend(values)
        return expansions

    def _narration_lines(self, script: dict[str, Any], story_beats: dict[str, Any]) -> list[str]:
        lines = script.get("narration_lines")
        if isinstance(lines, list) and lines:
            return [str(line) for line in lines]

        beat_lines = [
            str(value)
            for key, value in story_beats.items()
            if isinstance(value, str) and key != "emotion_curve"
        ]
        if beat_lines:
            return beat_lines

        raise ValueError("script.json must contain narration_lines or story_beats must contain text beats.")

    def _episode_id(
        self,
        knowledge_pack: dict[str, Any],
        script: dict[str, Any],
        output_dir: Path,
    ) -> str:
        for source in (script, knowledge_pack):
            value = source.get("episode_id") or source.get("episode")
            if value:
                return str(value)
        return output_dir.name

    def _episode_number(self, episode_id: str) -> str:
        match = re.search(r"(\d+)$", episode_id)
        if not match:
            return episode_id
        return match.group(1).zfill(3)

    def _candidate_title(self, source: str, media_type: str, query: str) -> str:
        return f"{source} {media_type} search: {query}".strip()

    def _search_url(self, source: str, media_type: str, query: str) -> str:
        encoded_query = urllib.parse.quote_plus(query)
        if source == "NASA":
            media_value = "image" if media_type == "image" else "video"
            return f"https://images.nasa.gov/search-results?q={encoded_query}&media_type={media_value}"
        if source == "NOAA":
            return f"https://www.noaa.gov/search?query={encoded_query}+{media_type}"
        if source == "Wikimedia Commons":
            return f"https://commons.wikimedia.org/w/index.php?search={encoded_query}+filetype%3A{media_type}"
        if source == "ESA":
            return f"https://www.esa.int/esasearch?q={encoded_query}+{media_type}"
        if source == "Pexels":
            return f"https://www.pexels.com/search/{urllib.parse.quote(query)}%20{media_type}/"
        if source == "Pixabay":
            return f"https://pixabay.com/{'videos/search' if media_type == 'video' else 'images/search'}/{urllib.parse.quote(query)}/"
        return f"https://www.google.com/search?q={encoded_query}+{media_type}"

    def _license_for(self, source: str) -> str:
        licenses = {
            "NASA": "NASA public domain or official media usage terms; verify per asset.",
            "NOAA": "NOAA public domain or official media usage terms; verify per asset.",
            "ESA": "ESA official media usage terms; verify per asset.",
            "Wikimedia Commons": "Creative Commons/Public Domain varies by file; verify per asset.",
            "Pexels": "Pexels License; verify per asset.",
            "Pixabay": "Pixabay Content License; verify per asset.",
        }
        return licenses[source]

    def _render_markdown(self, candidates: dict[str, object]) -> str:
        lines = [
            "# Asset Candidates",
            "",
            f"- Episode: {candidates.get('episode_id', candidates.get('episode'))}",
            "- Download: not performed",
            "- Source priority: " + ", ".join(SOURCE_PRIORITY),
            "",
        ]

        scene_keys = [key for key in candidates if re.fullmatch(r"scene_\d+", key)]
        for scene_key in sorted(scene_keys):
            scene_candidates = candidates.get(scene_key, [])
            lines.append(f"## {scene_key}")
            lines.append("")
            for index, candidate in enumerate(scene_candidates, start=1):
                if not isinstance(candidate, dict):
                    continue
                keywords = ", ".join(str(item) for item in candidate.get("keywords", []))
                lines.extend(
                    [
                        f"### 추천 {index}",
                        f"- Title: {candidate.get('title')}",
                        f"- Source: {candidate.get('source')} / {candidate.get('media_type')} / trust {candidate.get('trust_score')}",
                        f"- URL: {candidate.get('url')}",
                        f"- License: {candidate.get('license')}",
                        f"- Keywords: {keywords}",
                        "",
                    ]
                )

        return "\n".join(lines)

    def _flatten_text(self, value: Any) -> str:
        if isinstance(value, dict):
            return " ".join(self._flatten_text(item) for item in value.values())
        if isinstance(value, list):
            return " ".join(self._flatten_text(item) for item in value)
        return str(value or "")

    def _unique_keywords(self, keywords: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for keyword in keywords:
            cleaned = re.sub(r"\s+", " ", str(keyword).strip().lower())
            if len(cleaned) < 3 or cleaned in seen:
                continue
            seen.add(cleaned)
            unique.append(cleaned)
        return unique

    def _load_json(self, path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(path)
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} must contain a JSON object.")
        return value

    def _stop_words(self) -> set[str]:
        return {
            "and",
            "are",
            "but",
            "can",
            "com",
            "for",
            "from",
            "https",
            "into",
            "json",
            "not",
            "official",
            "org",
            "the",
            "this",
            "url",
            "was",
            "with",
            "www",
        }

    def _high_signal_words(self) -> set[str]:
        return {
            "astronaut",
            "climate",
            "deep",
            "earth",
            "esa",
            "hurricane",
            "iss",
            "mariana",
            "mars",
            "microgravity",
            "nasa",
            "noaa",
            "ocean",
            "orbit",
            "satellite",
            "space",
            "submarine",
            "trench",
            "underwater",
            "weather",
        }
