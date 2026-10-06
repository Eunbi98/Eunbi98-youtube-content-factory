from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from provider_models import MediaCandidate


class MediaDownloadError(RuntimeError):
    pass


class MediaDownloader:
    def __init__(
        self,
        *,
        timeout_seconds: float = 45.0,
        chunk_size: int = 1024 * 256,
    ) -> None:
        self.timeout_seconds = timeout_seconds
        self.chunk_size = chunk_size
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": (
                    "YouTubeContentFactory/7.5"
                )
            }
        )
        retry = Retry(
            total=3,
            backoff_factor=2.0,
            status_forcelist=(
                429,
                500,
                502,
                503,
                504,
            ),
            allowed_methods={"GET"},
            respect_retry_after_header=True,
        )
        self.session.mount(
            "https://",
            HTTPAdapter(max_retries=retry),
        )

    def download(
        self,
        *,
        candidate: MediaCandidate,
        destination_dir: Path,
        scene_id: str,
    ) -> Path:
        destination_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        extension = (
            candidate.file_extension
            or Path(
                urlparse(
                    candidate.download_url
                ).path
            ).suffix.lower()
            or ".jpg"
        )

        destination = (
            destination_dir
            / f"{scene_id}{extension}"
        )

        temporary = destination.with_suffix(
            f"{destination.suffix}.part"
        )

        try:
            with self.session.get(
                candidate.download_url,
                stream=True,
                timeout=self.timeout_seconds,
            ) as response:
                response.raise_for_status()

                with temporary.open("wb") as file:
                    for chunk in (
                        response.iter_content(
                            chunk_size=self.chunk_size
                        )
                    ):
                        if chunk:
                            file.write(chunk)

            if temporary.stat().st_size <= 0:
                raise MediaDownloadError(
                    "다운로드된 파일 크기가 0입니다."
                )

            temporary.replace(destination)
        except (
            requests.RequestException,
            OSError,
        ) as exc:
            if temporary.exists():
                temporary.unlink()

            raise MediaDownloadError(
                "미디어 다운로드에 실패했습니다.\n"
                f"장면: {scene_id}\n"
                f"주소: {candidate.download_url}\n"
                f"원인: {exc}"
            ) from exc

        return destination

    @staticmethod
    def file_sha256(
        file_path: Path,
    ) -> str:
        digest = hashlib.sha256()

        with file_path.open("rb") as file:
            while True:
                chunk = file.read(
                    1024 * 1024
                )

                if not chunk:
                    break

                digest.update(chunk)

        return digest.hexdigest()
