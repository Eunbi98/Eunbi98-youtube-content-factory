from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import random
import shutil
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlparse

import requests
from requests import Response
from requests.adapters import HTTPAdapter


DEFAULT_USER_AGENT = (
    "YouTubeContentFactory/6.5 "
    "(MediaCollector; contact: local-development)"
)

DEFAULT_TIMEOUT_SECONDS = 20.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF_SECONDS = 1.0
DEFAULT_CHUNK_SIZE = 1024 * 256


class HttpClientError(RuntimeError):
    """HTTP 요청 또는 파일 다운로드 실패."""


@dataclass(
    frozen=True,
    slots=True,
)
class HttpClientConfig:
    user_agent: str = DEFAULT_USER_AGENT
    timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS
    max_retries: int = DEFAULT_MAX_RETRIES
    backoff_seconds: float = DEFAULT_BACKOFF_SECONDS
    chunk_size: int = DEFAULT_CHUNK_SIZE
    verify_ssl: bool = True

    def __post_init__(self) -> None:
        normalized_user_agent = self.user_agent.strip()

        if not normalized_user_agent:
            raise ValueError(
                "user_agent는 비어 있을 수 없습니다."
            )

        if self.timeout_seconds <= 0:
            raise ValueError(
                "timeout_seconds는 0보다 커야 합니다."
            )

        if self.max_retries < 0:
            raise ValueError(
                "max_retries는 0 이상이어야 합니다."
            )

        if self.backoff_seconds < 0:
            raise ValueError(
                "backoff_seconds는 0 이상이어야 합니다."
            )

        if self.chunk_size <= 0:
            raise ValueError(
                "chunk_size는 0보다 커야 합니다."
            )

        object.__setattr__(
            self,
            "user_agent",
            normalized_user_agent,
        )


@dataclass(
    frozen=True,
    slots=True,
)
class DownloadResult:
    url: str
    output_path: Path
    file_size_bytes: int
    sha256: str
    content_type: str | None
    reused: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "outputPath": str(
                self.output_path
            ),
            "fileSizeBytes": (
                self.file_size_bytes
            ),
            "sha256": self.sha256,
            "contentType": (
                self.content_type
            ),
            "reused": self.reused,
        }


class HttpClient:
    """
    Media Provider 공통 HTTP 클라이언트입니다.

    지원 기능:
    - JSON GET 요청
    - 일반 GET 요청
    - 파일 다운로드
    - 재시도와 지수 백오프
    - SHA256 계산
    - 기존 다운로드 파일 재사용
    - 임시 파일 기반 안전 저장
    """

    def __init__(
        self,
        config: HttpClientConfig | None = None,
    ) -> None:
        self.config = (
            config
            if config is not None
            else HttpClientConfig()
        )

        self._session = requests.Session()

        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=10,
        )

        self._session.mount(
            "https://",
            adapter,
        )

        self._session.mount(
            "http://",
            adapter,
        )

        self._session.headers.update(
            {
                "User-Agent": (
                    self.config.user_agent
                ),
                "Accept": "*/*",
            }
        )

    def close(self) -> None:
        self._session.close()

    def __enter__(self) -> "HttpClient":
        return self

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> None:
        self.close()

    def get(
        self,
        url: str,
        *,
        params: Mapping[
            str,
            object,
        ] | None = None,
        headers: Mapping[
            str,
            str,
        ] | None = None,
        timeout_seconds: float | None = None,
    ) -> Response:
        return self._request_with_retry(
            method="GET",
            url=url,
            params=params,
            headers=headers,
            timeout_seconds=timeout_seconds,
            stream=False,
        )

    def get_json(
        self,
        url: str,
        *,
        params: Mapping[
            str,
            object,
        ] | None = None,
        headers: Mapping[
            str,
            str,
        ] | None = None,
        timeout_seconds: float | None = None,
    ) -> dict[str, Any]:
        response = self.get(
            url,
            params=params,
            headers=headers,
            timeout_seconds=timeout_seconds,
        )

        try:
            payload = response.json()

        except requests.JSONDecodeError as exc:
            preview = response.text[:500]

            raise HttpClientError(
                "HTTP 응답이 올바른 JSON이 아닙니다.\n"
                f"URL: {url}\n"
                f"상태 코드: {response.status_code}\n"
                f"응답 일부: {preview}"
            ) from exc

        if not isinstance(
            payload,
            dict,
        ):
            raise HttpClientError(
                "JSON 최상위 데이터가 객체가 아닙니다.\n"
                f"URL: {url}\n"
                f"데이터 형식: {type(payload).__name__}"
            )

        return payload

    def download(
        self,
        *,
        url: str,
        output_path: Path,
        headers: Mapping[
            str,
            str,
        ] | None = None,
        overwrite: bool = False,
        expected_sha256: str | None = None,
        minimum_size_bytes: int = 1,
        show_progress: bool = True,
    ) -> DownloadResult:
        normalized_url = self._normalize_url(
            url
        )

        resolved_output = (
            output_path.resolve()
        )

        if minimum_size_bytes <= 0:
            raise ValueError(
                "minimum_size_bytes는 "
                "1 이상이어야 합니다."
            )

        if (
            resolved_output.exists()
            and not overwrite
        ):
            return self._build_existing_result(
                url=normalized_url,
                output_path=resolved_output,
                expected_sha256=expected_sha256,
                minimum_size_bytes=(
                    minimum_size_bytes
                ),
            )

        resolved_output.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = (
            resolved_output.with_suffix(
                f"{resolved_output.suffix}.part"
            )
        )

        if temporary_path.exists():
            temporary_path.unlink()

        response = self._request_with_retry(
            method="GET",
            url=normalized_url,
            headers=headers,
            stream=True,
        )

        content_type = response.headers.get(
            "Content-Type"
        )

        total_size = self._read_content_length(
            response
        )

        downloaded_size = 0
        hasher = hashlib.sha256()

        try:
            with temporary_path.open(
                "wb"
            ) as file:
                for chunk in response.iter_content(
                    chunk_size=(
                        self.config.chunk_size
                    )
                ):
                    if not chunk:
                        continue

                    file.write(chunk)
                    hasher.update(chunk)

                    downloaded_size += len(
                        chunk
                    )

                    if show_progress:
                        self._print_progress(
                            filename=(
                                resolved_output.name
                            ),
                            downloaded_size=(
                                downloaded_size
                            ),
                            total_size=(
                                total_size
                            ),
                        )

            if show_progress:
                print()

            if (
                downloaded_size
                < minimum_size_bytes
            ):
                raise HttpClientError(
                    "다운로드 파일 크기가 "
                    "최소 기준보다 작습니다.\n"
                    f"URL: {normalized_url}\n"
                    f"크기: {downloaded_size} bytes\n"
                    f"최소: {minimum_size_bytes} bytes"
                )

            calculated_sha256 = (
                hasher.hexdigest()
            )

            self._validate_sha256(
                calculated=(
                    calculated_sha256
                ),
                expected=expected_sha256,
                url=normalized_url,
            )

            temporary_path.replace(
                resolved_output
            )

        except Exception:
            if temporary_path.exists():
                temporary_path.unlink()

            raise

        return DownloadResult(
            url=normalized_url,
            output_path=resolved_output,
            file_size_bytes=(
                downloaded_size
            ),
            sha256=calculated_sha256,
            content_type=content_type,
            reused=False,
        )

    def download_to_directory(
        self,
        *,
        url: str,
        output_dir: Path,
        filename: str | None = None,
        overwrite: bool = False,
        expected_sha256: str | None = None,
        minimum_size_bytes: int = 1,
        show_progress: bool = True,
    ) -> DownloadResult:
        resolved_filename = (
            filename
            if filename
            else self.guess_filename(
                url
            )
        )

        output_path = (
            output_dir
            / resolved_filename
        )

        return self.download(
            url=url,
            output_path=output_path,
            overwrite=overwrite,
            expected_sha256=(
                expected_sha256
            ),
            minimum_size_bytes=(
                minimum_size_bytes
            ),
            show_progress=show_progress,
        )

    @staticmethod
    def calculate_sha256(
        file_path: Path,
        *,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
    ) -> str:
        resolved_path = file_path.resolve()

        if not resolved_path.exists():
            raise HttpClientError(
                "SHA256을 계산할 파일이 없습니다:\n"
                f"{resolved_path}"
            )

        if not resolved_path.is_file():
            raise HttpClientError(
                "SHA256 경로가 파일이 아닙니다:\n"
                f"{resolved_path}"
            )

        hasher = hashlib.sha256()

        with resolved_path.open(
            "rb"
        ) as file:
            while True:
                chunk = file.read(
                    chunk_size
                )

                if not chunk:
                    break

                hasher.update(chunk)

        return hasher.hexdigest()

    @staticmethod
    def guess_filename(
        url: str,
        *,
        fallback_name: str = "download",
        content_type: str | None = None,
    ) -> str:
        parsed_url = urlparse(
            url
        )

        path_name = Path(
            parsed_url.path
        ).name

        if path_name:
            return path_name

        extension = None

        if content_type:
            normalized_content_type = (
                content_type
                .split(";")[0]
                .strip()
                .lower()
            )

            extension = (
                mimetypes.guess_extension(
                    normalized_content_type
                )
            )

        if extension:
            return (
                f"{fallback_name}"
                f"{extension}"
            )

        return fallback_name

    def save_json(
        self,
        *,
        payload: Mapping[
            str,
            Any,
        ],
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
                f"{resolved_path.suffix}.part"
            )
        )

        try:
            temporary_path.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            temporary_path.replace(
                resolved_path
            )

        except OSError as exc:
            if temporary_path.exists():
                temporary_path.unlink()

            raise HttpClientError(
                "JSON 파일 저장에 실패했습니다.\n"
                f"파일: {resolved_path}\n"
                f"원인: {exc}"
            ) from exc

    def _request_with_retry(
        self,
        *,
        method: str,
        url: str,
        params: Mapping[
            str,
            object,
        ] | None = None,
        headers: Mapping[
            str,
            str,
        ] | None = None,
        timeout_seconds: float | None = None,
        stream: bool = False,
    ) -> Response:
        normalized_url = self._normalize_url(
            url
        )

        resolved_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else self.config.timeout_seconds
        )

        last_error: Exception | None = None

        for attempt in range(
            self.config.max_retries + 1
        ):
            try:
                response = (
                    self._session.request(
                        method=method,
                        url=normalized_url,
                        params=params,
                        headers=headers,
                        timeout=(
                            resolved_timeout
                        ),
                        verify=(
                            self.config.verify_ssl
                        ),
                        stream=stream,
                    )
                )

                if (
                    response.status_code
                    in {
                        408,
                        425,
                        429,
                        500,
                        502,
                        503,
                        504,
                    }
                ):
                    if (
                        attempt
                        >= self.config.max_retries
                    ):
                        self._raise_for_status(
                            response
                        )

                    response.close()

                    self._sleep_before_retry(
                        attempt=attempt,
                        retry_after=response.headers.get(
                            "Retry-After"
                        ),
                    )

                    continue

                self._raise_for_status(
                    response
                )

                return response

            except (
                requests.Timeout,
                requests.ConnectionError,
            ) as exc:
                last_error = exc

                if (
                    attempt
                    >= self.config.max_retries
                ):
                    break

                self._sleep_before_retry(
                    attempt=attempt,
                    retry_after=None,
                )

            except requests.RequestException as exc:
                raise HttpClientError(
                    "HTTP 요청에 실패했습니다.\n"
                    f"URL: {normalized_url}\n"
                    f"원인: {exc}"
                ) from exc

        raise HttpClientError(
            "HTTP 요청 재시도 횟수를 "
            "초과했습니다.\n"
            f"URL: {normalized_url}\n"
            f"재시도: "
            f"{self.config.max_retries}회\n"
            f"원인: {last_error}"
        ) from last_error

    def _sleep_before_retry(
        self,
        *,
        attempt: int,
        retry_after: str | None,
    ) -> None:
        retry_after_seconds = (
            self._parse_retry_after(
                retry_after
            )
        )

        if retry_after_seconds is not None:
            delay = retry_after_seconds

        else:
            exponential_delay = (
                self.config.backoff_seconds
                * (2 ** attempt)
            )

            jitter = random.uniform(
                0,
                max(
                    0.1,
                    self.config.backoff_seconds
                    * 0.25,
                ),
            )

            delay = (
                exponential_delay
                + jitter
            )

        print(
            "[재시도] "
            f"{delay:.2f}초 후 "
            "HTTP 요청을 다시 실행합니다."
        )

        time.sleep(delay)

    @staticmethod
    def _parse_retry_after(
        retry_after: str | None,
    ) -> float | None:
        if not retry_after:
            return None

        try:
            value = float(
                retry_after.strip()
            )

        except ValueError:
            return None

        if value < 0:
            return None

        return value

    @staticmethod
    def _raise_for_status(
        response: Response,
    ) -> None:
        try:
            response.raise_for_status()

        except requests.HTTPError as exc:
            preview = ""

            try:
                preview = (
                    response.text[:500]
                )

            except Exception:
                preview = (
                    "<응답 본문을 읽을 수 없음>"
                )

            raise HttpClientError(
                "HTTP 응답 오류입니다.\n"
                f"URL: {response.url}\n"
                f"상태 코드: "
                f"{response.status_code}\n"
                f"응답 일부: {preview}"
            ) from exc

    def _build_existing_result(
        self,
        *,
        url: str,
        output_path: Path,
        expected_sha256: str | None,
        minimum_size_bytes: int,
    ) -> DownloadResult:
        file_size = (
            output_path
            .stat()
            .st_size
        )

        if (
            file_size
            < minimum_size_bytes
        ):
            raise HttpClientError(
                "기존 파일 크기가 "
                "최소 기준보다 작습니다.\n"
                f"파일: {output_path}\n"
                f"크기: {file_size} bytes"
            )

        calculated_sha256 = (
            self.calculate_sha256(
                output_path
            )
        )

        self._validate_sha256(
            calculated=(
                calculated_sha256
            ),
            expected=expected_sha256,
            url=url,
        )

        print(
            "[건너뜀] 기존 다운로드 파일 사용: "
            f"{output_path}"
        )

        return DownloadResult(
            url=url,
            output_path=output_path,
            file_size_bytes=file_size,
            sha256=calculated_sha256,
            content_type=None,
            reused=True,
        )

    @staticmethod
    def _validate_sha256(
        *,
        calculated: str,
        expected: str | None,
        url: str,
    ) -> None:
        if expected is None:
            return

        normalized_expected = (
            expected
            .strip()
            .lower()
        )

        normalized_calculated = (
            calculated
            .strip()
            .lower()
        )

        if (
            normalized_expected
            != normalized_calculated
        ):
            raise HttpClientError(
                "SHA256 검증에 실패했습니다.\n"
                f"URL: {url}\n"
                f"예상: {normalized_expected}\n"
                f"실제: {normalized_calculated}"
            )

    @staticmethod
    def _normalize_url(
        url: str,
    ) -> str:
        normalized_url = (
            url.strip()
        )

        if not normalized_url:
            raise ValueError(
                "URL은 비어 있을 수 없습니다."
            )

        parsed = urlparse(
            normalized_url
        )

        if parsed.scheme not in {
            "http",
            "https",
        }:
            raise ValueError(
                "지원하지 않는 URL 형식입니다: "
                f"{normalized_url}"
            )

        if not parsed.netloc:
            raise ValueError(
                "URL에 호스트가 없습니다: "
                f"{normalized_url}"
            )

        return normalized_url

    @staticmethod
    def _read_content_length(
        response: Response,
    ) -> int | None:
        raw_length = (
            response.headers.get(
                "Content-Length"
            )
        )

        if not raw_length:
            return None

        try:
            parsed_length = int(
                raw_length
            )

        except ValueError:
            return None

        if parsed_length <= 0:
            return None

        return parsed_length

    @staticmethod
    def _print_progress(
        *,
        filename: str,
        downloaded_size: int,
        total_size: int | None,
    ) -> None:
        if total_size:
            percentage = min(
                100.0,
                (
                    downloaded_size
                    / total_size
                )
                * 100,
            )

            message = (
                f"\r[다운로드] {filename} "
                f"{percentage:6.2f}% "
                f"({downloaded_size:,}/"
                f"{total_size:,} bytes)"
            )

        else:
            message = (
                f"\r[다운로드] {filename} "
                f"{downloaded_size:,} bytes"
            )

        print(
            message,
            end="",
            flush=True,
        )


def build_config_from_environment(
) -> HttpClientConfig:
    return HttpClientConfig(
        user_agent=os.getenv(
            "YCF_HTTP_USER_AGENT",
            DEFAULT_USER_AGENT,
        ),
        timeout_seconds=(
            _read_float_environment(
                name=(
                    "YCF_HTTP_TIMEOUT_SECONDS"
                ),
                default=(
                    DEFAULT_TIMEOUT_SECONDS
                ),
            )
        ),
        max_retries=(
            _read_int_environment(
                name=(
                    "YCF_HTTP_MAX_RETRIES"
                ),
                default=(
                    DEFAULT_MAX_RETRIES
                ),
            )
        ),
        backoff_seconds=(
            _read_float_environment(
                name=(
                    "YCF_HTTP_BACKOFF_SECONDS"
                ),
                default=(
                    DEFAULT_BACKOFF_SECONDS
                ),
            )
        ),
        chunk_size=(
            _read_int_environment(
                name=(
                    "YCF_HTTP_CHUNK_SIZE"
                ),
                default=(
                    DEFAULT_CHUNK_SIZE
                ),
            )
        ),
        verify_ssl=(
            _read_bool_environment(
                name=(
                    "YCF_HTTP_VERIFY_SSL"
                ),
                default=True,
            )
        ),
    )


def _read_int_environment(
    *,
    name: str,
    default: int,
) -> int:
    raw_value = os.getenv(
        name
    )

    if (
        raw_value is None
        or not raw_value.strip()
    ):
        return default

    try:
        return int(
            raw_value.strip()
        )

    except ValueError as exc:
        raise ValueError(
            f"{name} 환경변수는 "
            "정수여야 합니다: "
            f"{raw_value}"
        ) from exc


def _read_float_environment(
    *,
    name: str,
    default: float,
) -> float:
    raw_value = os.getenv(
        name
    )

    if (
        raw_value is None
        or not raw_value.strip()
    ):
        return default

    try:
        return float(
            raw_value.strip()
        )

    except ValueError as exc:
        raise ValueError(
            f"{name} 환경변수는 "
            "숫자여야 합니다: "
            f"{raw_value}"
        ) from exc


def _read_bool_environment(
    *,
    name: str,
    default: bool,
) -> bool:
    raw_value = os.getenv(
        name
    )

    if (
        raw_value is None
        or not raw_value.strip()
    ):
        return default

    normalized = (
        raw_value
        .strip()
        .lower()
    )

    if normalized in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "no",
        "n",
        "off",
    }:
        return False

    raise ValueError(
        f"{name} 환경변수 값이 "
        "올바르지 않습니다: "
        f"{raw_value}"
    )


def main() -> int:
    config = (
        build_config_from_environment()
    )

    with HttpClient(
        config=config
    ) as client:
        payload = client.get_json(
            "https://commons.wikimedia.org/"
            "w/api.php",
            params={
                "action": "query",
                "format": "json",
                "meta": "siteinfo",
                "siprop": "general",
            },
        )

    query = payload.get(
        "query",
        {}
    )

    general = (
        query.get(
            "general",
            {}
        )
        if isinstance(
            query,
            dict,
        )
        else {}
    )

    site_name = (
        general.get(
            "sitename",
            "unknown",
        )
        if isinstance(
            general,
            dict,
        )
        else "unknown"
    )

    print("=" * 62)
    print(
        " YouTube Content Factory "
        "HTTP Client"
    )
    print("=" * 62)
    print(
        f"{'site':>18}: "
        f"{site_name}"
    )
    print(
        f"{'timeout':>18}: "
        f"{config.timeout_seconds}초"
    )
    print(
        f"{'max_retries':>18}: "
        f"{config.max_retries}"
    )
    print("-" * 62)
    print(
        "[성공] HTTP Client "
        "공식 API 연결 완료"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )