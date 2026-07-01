from pathlib import Path

import requests
from bs4 import BeautifulSoup


class ImageService:

    def __init__(self):

        self.output_dir = Path("output/images")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def download_image(self, article):

        if not article.link:
            return None

        try:

            response = requests.get(
                article.link,
                timeout=10,
                headers={
                    "User-Agent":
                    "Mozilla/5.0"
                }
            )

            soup = BeautifulSoup(response.text, "html.parser")

            meta = soup.find(
                "meta",
                property="og:image"
            )

            if meta is None:
                return None

            image_url = meta.get("content")

            if not image_url:
                return None

            image = requests.get(
                image_url,
                timeout=10
            )

            image.raise_for_status()

            output_path = self.output_dir / "news.jpg"

            with open(output_path, "wb") as f:
                f.write(image.content)

            return str(output_path)

        except Exception as e:

            print("이미지 다운로드 실패")
            print(e)

            return None