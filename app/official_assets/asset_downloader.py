from __future__ import annotations

import json
import mimetypes
import re
import shutil
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.official_assets.asset_types import SOURCE_PRIORITY


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}


@dataclass(frozen=True)
class ResolvedAsset:
    title: str
    source: str
    original_url: str
    download_url: str
    license: str
    media_type: str
    keywords: list[str]
    trust_score: int


class OfficialAssetDownloader:
    def __init__(
        self,
        *,
        max_assets_per_scene: int = 2,
        max_bytes: int = 30_000_000,
        request_timeout_seconds: float = 20,
    ) -> None:
        self.max_assets_per_scene = max_assets_per_scene
        self.max_bytes = max_bytes
        self.request_timeout_seconds = request_timeout_seconds

    def download_from_file(
        self,
        asset_candidates_path: Path | str,
        output_dir: Path | str | None = None,
    ) -> dict[str, object]:
        candidates_file = Path(asset_candidates_path)
        target_dir = Path(output_dir) if output_dir else candidates_file.parent / "assets"
        candidates = self._load_json(candidates_file)
        manifest = self.download(candidates, target_dir)

        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / "sources.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (target_dir / "download_report.md").write_text(
            self._render_report(manifest),
            encoding="utf-8",
        )
        return manifest

    def download(
        self,
        candidates: dict[str, Any],
        output_dir: Path,
    ) -> dict[str, object]:
        images_dir = output_dir / "images"
        videos_dir = output_dir / "videos"
        licenses_dir = output_dir / "licenses"
        for directory in (images_dir, videos_dir, licenses_dir):
            directory.mkdir(parents=True, exist_ok=True)

        manifest: dict[str, object] = {
            "episode": candidates.get("episode"),
            "episode_id": candidates.get("episode_id"),
            "download_policy": "selected_candidates_only",
            "max_assets_per_scene": self.max_assets_per_scene,
            "max_bytes": self.max_bytes,
            "assets": [],
            "skipped": [],
        }

        scene_keys = sorted(key for key in candidates if re.fullmatch(r"scene_\d+", key))
        for scene_key in scene_keys:
            selected_for_scene = 0
            scene_candidates = candidates.get(scene_key, [])
            if not isinstance(scene_candidates, list):
                continue

            for candidate in self._sort_candidates(scene_candidates):
                if selected_for_scene >= self.max_assets_per_scene:
                    break

                try:
                    resolved = self._resolve_candidate(candidate, scene_key)
                    if not resolved:
                        self._add_skip(manifest, scene_key, candidate, "No direct downloadable asset could be resolved.")
                        continue
                    asset_record = self._download_resolved_asset(
                        scene_key=scene_key,
                        resolved=resolved,
                        images_dir=images_dir,
                        videos_dir=videos_dir,
                        licenses_dir=licenses_dir,
                    )
                except Exception as exc:
                    self._add_skip(manifest, scene_key, candidate, f"{type(exc).__name__}: {exc}")
                    continue

                manifest["assets"].append(asset_record)
                selected_for_scene += 1

        return manifest

    def _resolve_candidate(self, candidate: dict[str, Any], scene_key: str) -> ResolvedAsset | None:
        source = str(candidate.get("source", ""))
        url = str(candidate.get("url", ""))
        media_type = str(candidate.get("media_type", "image"))

        direct_url = self._direct_file_url(url, media_type)
        license_text = str(candidate.get("license", "Usage terms must be verified per asset."))
        title = str(candidate.get("title", "official asset"))

        if not direct_url and source == "NASA":
            nasa_asset = self._resolve_nasa(candidate)
            if nasa_asset:
                direct_url, title, license_text, media_type = nasa_asset

        if not direct_url and source == "NOAA":
            noaa_asset = self._resolve_noaa(candidate, scene_key)
            if noaa_asset:
                direct_url, title, license_text, media_type = noaa_asset

        if not direct_url and source == "Wikimedia Commons":
            wikimedia_asset = self._resolve_wikimedia(candidate)
            if wikimedia_asset:
                direct_url, title, license_text, media_type = wikimedia_asset

        if not direct_url:
            return None

        return ResolvedAsset(
            title=title,
            source=source,
            original_url=url,
            download_url=direct_url,
            license=license_text,
            media_type=media_type,
            keywords=[str(item) for item in candidate.get("keywords", [])],
            trust_score=int(candidate.get("trust_score", 0)),
        )

    def _resolve_nasa(self, candidate: dict[str, Any]) -> tuple[str, str, str, str] | None:
        original_url = str(candidate.get("url", ""))
        parsed = urllib.parse.urlparse(original_url)
        params = urllib.parse.parse_qs(parsed.query)
        query = (params.get("q") or [" ".join(candidate.get("keywords", []))])[0]
        media_type = (params.get("media_type") or [candidate.get("media_type", "image")])[0]
        if media_type not in {"image", "video"}:
            media_type = str(candidate.get("media_type", "image"))

        api_url = "https://images-api.nasa.gov/search?" + urllib.parse.urlencode(
            {
                "q": query,
                "media_type": media_type,
            }
        )
        payload = self._fetch_json(api_url)
        items = payload.get("collection", {}).get("items", [])

        for item in items[:8]:
            data_items = item.get("data", [])
            data = data_items[0] if data_items else {}
            item_media_type = data.get("media_type", media_type)
            if item_media_type not in {"image", "video"}:
                continue
            asset_url = self._nasa_download_url(item, item_media_type)
            if not asset_url:
                continue
            title = data.get("title") or str(candidate.get("title", "NASA asset"))
            return (
                asset_url,
                title,
                "NASA public domain or official media usage terms; verify per asset.",
                item_media_type,
            )

        return None

    def _nasa_download_url(self, item: dict[str, Any], media_type: str) -> str | None:
        asset_collection_url = item.get("href")
        if asset_collection_url:
            try:
                payload = self._fetch_json(str(asset_collection_url))
                urls = [
                    str(asset.get("href", ""))
                    for asset in payload.get("collection", {}).get("items", [])
                    if asset.get("href")
                ]
                preferred_extensions = IMAGE_EXTENSIONS if media_type == "image" else VIDEO_EXTENSIONS
                filtered = [
                    url
                    for url in urls
                    if self._extension_from_url(url) in preferred_extensions
                ]
                if media_type == "image":
                    filtered.sort(key=lambda url: ("~orig" not in url.lower(), len(url)))
                if filtered:
                    return filtered[0]
            except Exception:
                pass

        for link in item.get("links", []):
            href = str(link.get("href", ""))
            if href and self._extension_from_url(href) in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
                return href

        return None

    def _resolve_wikimedia(self, candidate: dict[str, Any]) -> tuple[str, str, str, str] | None:
        original_url = str(candidate.get("url", ""))
        parsed = urllib.parse.urlparse(original_url)
        params = urllib.parse.parse_qs(parsed.query)
        query = (params.get("search") or [" ".join(candidate.get("keywords", []))])[0]
        query = query.replace("filetype:image", "").replace("filetype:video", "").strip()
        desired_media_type = str(candidate.get("media_type", "image"))
        queries = [query]
        if desired_media_type == "video":
            queries.extend(
                [
                    "deep sea video",
                    "underwater deep sea video",
                    "submersible underwater video",
                    "hydrothermal vent video",
                ]
            )

        for search_query in self._unique_strings(queries):
            api_url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(
                {
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": search_query,
                    "gsrnamespace": 6,
                    "gsrlimit": 10,
                    "prop": "imageinfo",
                    "iiprop": "url|extmetadata|mime|size",
                    "format": "json",
                }
            )
            payload = self._fetch_json(api_url)
            pages = payload.get("query", {}).get("pages", {})
            for page in pages.values():
                image_info = (page.get("imageinfo") or [{}])[0]
                download_url = image_info.get("url")
                if not download_url:
                    continue
                extension = self._extension_from_url(str(download_url))
                if extension not in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS:
                    continue
                size = int(image_info.get("size") or 0)
                if size and size > self.max_bytes:
                    continue
                mime = str(image_info.get("mime", ""))
                media_type = "video" if mime.startswith("video/") else "image"
                if desired_media_type != media_type:
                    continue
                metadata = image_info.get("extmetadata", {})
                license_text = metadata.get("LicenseShortName", {}).get("value") or "Wikimedia Commons license; verify per asset."
                return (
                    str(download_url),
                    str(page.get("title") or candidate.get("title") or "Wikimedia asset"),
                    str(license_text),
                    media_type,
                )

        return None

    def _resolve_noaa(self, candidate: dict[str, Any], scene_key: str) -> tuple[str, str, str, str] | None:
        if str(candidate.get("media_type", "image")) != "image":
            return None

        page_url = "https://www.fisheries.noaa.gov/pacific-islands/habitat-conservation/mariana-trench-marine-national-monument"
        request = urllib.request.Request(
            page_url,
            headers={"User-Agent": "youtube-content-factory/official-asset-downloader"},
        )
        with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
            html = response.read().decode("utf-8", "ignore")

        image_urls = self._extract_image_urls_from_html(html, page_url)
        if not image_urls:
            return None
        scene_number = int(scene_key.split("_")[-1])
        selected_url = image_urls[(scene_number - 1) % len(image_urls)]

        return (
            selected_url,
            "NOAA Mariana Trench Marine National Monument image",
            "NOAA public domain or official media usage terms; verify per asset.",
            "image",
        )

    def _download_resolved_asset(
        self,
        *,
        scene_key: str,
        resolved: ResolvedAsset,
        images_dir: Path,
        videos_dir: Path,
        licenses_dir: Path,
    ) -> dict[str, object]:
        extension = self._extension_from_url(resolved.download_url)
        allowed_extensions = VIDEO_EXTENSIONS if resolved.media_type == "video" else IMAGE_EXTENSIONS
        if extension and extension not in allowed_extensions:
            raise ValueError(f"Unsupported {resolved.media_type} extension: {extension}")
        if not extension:
            extension = self._extension_from_content_type(resolved.download_url, resolved.media_type)

        target_root = videos_dir if resolved.media_type == "video" else images_dir
        cleaned_title = self._title_without_extension(resolved.title)
        filename = self._safe_filename(
            f"{scene_key}_{resolved.source}_{resolved.media_type}_{cleaned_title}"
        )
        target_path = self._unique_path(target_root / f"{filename}{extension}")

        bytes_written, content_type = self._download_file(resolved.download_url, target_path)
        license_record = {
            "scene": scene_key,
            "title": resolved.title,
            "source": resolved.source,
            "original_url": resolved.original_url,
            "download_url": resolved.download_url,
            "license": resolved.license,
            "media_type": resolved.media_type,
            "keywords": resolved.keywords,
            "trust_score": resolved.trust_score,
            "local_path": str(target_path),
            "bytes": bytes_written,
            "content_type": content_type,
        }
        license_path = licenses_dir / f"{target_path.stem}.license.json"
        license_path.write_text(
            json.dumps(license_record, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return {
            **license_record,
            "license_path": str(license_path),
        }

    def _download_file(self, url: str, target_path: Path) -> tuple[int, str]:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "youtube-content-factory/official-asset-downloader"},
        )
        with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
            content_type = response.headers.get("Content-Type", "")
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > self.max_bytes:
                raise ValueError(f"File is larger than max_bytes: {content_length}")

            bytes_written = 0
            with target_path.open("wb") as output:
                while True:
                    chunk = response.read(1024 * 256)
                    if not chunk:
                        break
                    bytes_written += len(chunk)
                    if bytes_written > self.max_bytes:
                        output.close()
                        target_path.unlink(missing_ok=True)
                        raise ValueError(f"Download exceeded max_bytes: {bytes_written}")
                    output.write(chunk)

        return bytes_written, content_type

    def _direct_file_url(self, url: str, media_type: str) -> str | None:
        extension = self._extension_from_url(url)
        allowed = VIDEO_EXTENSIONS if media_type == "video" else IMAGE_EXTENSIONS
        if extension in allowed:
            return url
        return None

    def _extract_image_urls_from_html(self, html: str, base_url: str) -> list[str]:
        candidates: list[str] = []
        patterns = [
            r'<a[^>]+href=["\']([^"\']+\.(?:jpg|jpeg|png)(?:\?[^"\']*)?)["\']',
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
            r'<img[^>]+src=["\']([^"\']+)["\']',
            r'<img[^>]+data-src=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            candidates.extend(re.findall(pattern, html, flags=re.IGNORECASE))

        urls: list[str] = []
        seen: set[str] = set()
        for candidate in candidates:
            url = urllib.parse.urljoin(base_url, candidate)
            extension = self._extension_from_url(url)
            if extension not in IMAGE_EXTENSIONS:
                continue
            lowered = url.lower()
            if (
                "open-graph" in lowered
                or "logo" in lowered
                or "scroll" in lowered
                or "icon_" in lowered
                or "/icons/" in lowered
            ):
                continue
            if url in seen:
                continue
            seen.add(url)
            urls.append(url)
        return urls

    def _sort_candidates(self, candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
        source_rank = {source: index for index, source in enumerate(SOURCE_PRIORITY)}
        media_rank = {"image": 0, "video": 1}
        return sorted(
            candidates,
            key=lambda candidate: (
                -int(candidate.get("trust_score", 0)),
                source_rank.get(str(candidate.get("source", "")), 99),
                media_rank.get(str(candidate.get("media_type", "")), 99),
            ),
        )

    def _fetch_json(self, url: str) -> dict[str, Any]:
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "youtube-content-factory/official-asset-downloader"},
        )
        with urllib.request.urlopen(request, timeout=self.request_timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))

    def _add_skip(
        self,
        manifest: dict[str, object],
        scene_key: str,
        candidate: dict[str, Any],
        reason: str,
    ) -> None:
        manifest["skipped"].append(
            {
                "scene": scene_key,
                "title": candidate.get("title"),
                "source": candidate.get("source"),
                "media_type": candidate.get("media_type"),
                "url": candidate.get("url"),
                "reason": reason,
            }
        )

    def _render_report(self, manifest: dict[str, object]) -> str:
        assets = manifest.get("assets", [])
        skipped = manifest.get("skipped", [])
        lines = [
            "# Official Asset Download Report",
            "",
            f"- Episode: {manifest.get('episode_id', manifest.get('episode'))}",
            f"- Downloaded assets: {len(assets)}",
            f"- Skipped candidates: {len(skipped)}",
            f"- Max bytes per asset: {manifest.get('max_bytes')}",
            "",
            "## Downloaded",
            "",
        ]
        for asset in assets:
            lines.extend(
                [
                    f"### {asset['scene']} - {asset['title']}",
                    f"- Source: {asset['source']}",
                    f"- Media type: {asset['media_type']}",
                    f"- Local path: `{asset['local_path']}`",
                    f"- License: {asset['license']}",
                    f"- Original URL: {asset['original_url']}",
                    f"- Download URL: {asset['download_url']}",
                    "",
                ]
            )

        lines.extend(["## Skipped", ""])
        for item in skipped[:80]:
            lines.append(
                f"- {item.get('scene')} / {item.get('source')} / {item.get('media_type')}: {item.get('reason')}"
            )
        lines.append("")
        return "\n".join(lines)

    def _extension_from_url(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        extension = Path(parsed.path).suffix.lower()
        if extension == ".jpeg":
            return ".jpg"
        return extension

    def _extension_from_content_type(self, url: str, media_type: str) -> str:
        guessed = mimetypes.guess_extension(media_type)
        if guessed:
            return guessed
        return ".mp4" if media_type == "video" else ".jpg"

    def _safe_filename(self, value: str) -> str:
        value = re.sub(r"[^\w가-힣.-]+", "_", value, flags=re.UNICODE)
        value = re.sub(r"_+", "_", value).strip("._")
        return value[:120] or "asset"

    def _title_without_extension(self, title: str) -> str:
        cleaned = str(title).removeprefix("File:")
        for extension in sorted(IMAGE_EXTENSIONS | VIDEO_EXTENSIONS, key=len, reverse=True):
            if cleaned.lower().endswith(extension):
                return cleaned[: -len(extension)]
        return cleaned

    def _unique_path(self, path: Path) -> Path:
        if not path.exists():
            return path
        index = 2
        while True:
            candidate = path.with_name(f"{path.stem}_{index}{path.suffix}")
            if not candidate.exists():
                return candidate
            index += 1

    def _unique_strings(self, values: list[str]) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for value in values:
            cleaned = re.sub(r"\s+", " ", str(value).strip())
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            unique.append(cleaned)
        return unique

    def _load_json(self, path: Path) -> dict[str, Any]:
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"{path} must contain a JSON object.")
        return value
