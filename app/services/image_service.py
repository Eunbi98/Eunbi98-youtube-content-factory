import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from config.settings import DEFAULT_IMAGE_FILENAME, IMAGE_DIR


class ImageService:
    def __init__(self):
        self.output_dir = IMAGE_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_image(self, article):
        if not article.link:
            return None

        try:
            response = requests.get(
                article.link,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            image_url = self._find_image_url(soup)

            if not image_url:
                return None

            image_url = urljoin(article.link, image_url)

            image = requests.get(
                image_url,
                timeout=10,
                headers={
                    "User-Agent": "Mozilla/5.0"
                }
            )
            image.raise_for_status()

            output_path = self.output_dir / DEFAULT_IMAGE_FILENAME

            with open(output_path, "wb") as f:
                f.write(image.content)

            return str(output_path)

        except Exception as e:
            print("이미지 다운로드 실패")
            print(e)
            return None

    def _find_image_url(self, soup: BeautifulSoup) -> str | None:
        meta = soup.find("meta", property="og:image")

        if meta and meta.get("content"):
            return meta.get("content")

        twitter_meta = soup.find("meta", attrs={"name": "twitter:image"})

        if twitter_meta and twitter_meta.get("content"):
            return twitter_meta.get("content")

        first_image = soup.find("img")

        if first_image and first_image.get("src"):
            src = first_image.get("src")

            if self._looks_like_image(src):
                return src

        return None

    def _looks_like_image(self, url: str) -> bool:
        return bool(
            re.search(
                r"\.(jpg|jpeg|png|webp)(\?.*)?$",
                url,
                re.IGNORECASE
            )
        )