import hashlib
from pathlib import Path
from urllib.parse import quote

import requests

from config.settings import SCENE_IMAGE_DIR, SCENE_IMAGE_LIMIT


class SceneImageService:
    def __init__(self):
        self.output_dir = SCENE_IMAGE_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.headers = {
            "User-Agent": "youtube-content-factory/1.0"
        }

    def download_scene_images(self, article, fallback_image_path: str | None = None) -> list[str]:
        if not article.scenes:
            return [fallback_image_path] if fallback_image_path else []

        image_paths = []

        for scene in article.scenes[:SCENE_IMAGE_LIMIT]:
            keyword = str(scene.get("image_keyword", "")).strip()

            if not keyword:
                keyword = article.title

            path = self._download_from_wikimedia(keyword)

            if path:
                image_paths.append(path)
            elif fallback_image_path:
                image_paths.append(fallback_image_path)

        if not image_paths and fallback_image_path:
            image_paths.append(fallback_image_path)

        return image_paths

    def _download_from_wikimedia(self, keyword: str) -> str | None:
        try:
            image_url = self._find_wikimedia_image_url(keyword)

            if not image_url:
                return None

            response = requests.get(
                image_url,
                timeout=15,
                headers=self.headers
            )
            response.raise_for_status()

            content_type = response.headers.get("Content-Type", "")

            if "image" not in content_type:
                return None

            ext = self._guess_extension(content_type, image_url)
            filename = self._make_filename(keyword, ext)
            output_path = self.output_dir / filename

            with open(output_path, "wb") as f:
                f.write(response.content)

            return str(output_path)

        except Exception:
            return None

    def _find_wikimedia_image_url(self, keyword: str) -> str | None:
        search_url = "https://commons.wikimedia.org/w/api.php"

        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": keyword,
            "gsrnamespace": 6,
            "gsrlimit": 5,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 1200
        }

        response = requests.get(
            search_url,
            params=params,
            timeout=15,
            headers=self.headers
        )
        response.raise_for_status()

        data = response.json()
        pages = data.get("query", {}).get("pages", {})

        for page in pages.values():
            image_info = page.get("imageinfo", [])

            if not image_info:
                continue

            item = image_info[0]
            url = item.get("thumburl") or item.get("url")

            if self._is_usable_image(url):
                return url

        return None

    def _is_usable_image(self, url: str | None) -> bool:
        if not url:
            return False

        lowered = url.lower()

        blocked = [
            ".svg",
            ".gif",
            "logo",
            "icon",
            "symbol"
        ]

        return not any(item in lowered for item in blocked)

    def _guess_extension(self, content_type: str, image_url: str) -> str:
        lowered = content_type.lower()

        if "png" in lowered:
            return ".png"

        if "webp" in lowered:
            return ".webp"

        if "jpeg" in lowered or "jpg" in lowered:
            return ".jpg"

        lowered_url = image_url.lower()

        for ext in [".jpg", ".jpeg", ".png", ".webp"]:
            if ext in lowered_url:
                return ext

        return ".jpg"

    def _make_filename(self, keyword: str, ext: str) -> str:
        safe_keyword = "".join(
            char for char in keyword[:40]
            if char.isalnum() or char in (" ", "_", "-")
        ).strip()

        safe_keyword = safe_keyword.replace(" ", "_")

        digest = hashlib.md5(keyword.encode("utf-8")).hexdigest()[:8]

        if not safe_keyword:
            safe_keyword = "scene"

        return f"{safe_keyword}_{digest}{ext}"