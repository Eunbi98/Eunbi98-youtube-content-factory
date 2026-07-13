from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class CacheManagerError(RuntimeError):
    pass


class CacheManager:
    def __init__(
        self,
        cache_dir: Path,
    ) -> None:
        self.cache_dir = cache_dir.resolve()
        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    def build_key(
        self,
        *parts: str,
    ) -> str:
        raw = "\n".join(parts)
        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

    def json_path(
        self,
        key: str,
    ) -> Path:
        return (
            self.cache_dir
            / f"{key}.json"
        )

    def load_json(
        self,
        key: str,
    ) -> dict[str, Any] | None:
        path = self.json_path(key)

        if not path.exists():
            return None

        try:
            data = json.loads(
                path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise CacheManagerError(
                "캐시 파일을 읽지 못했습니다.\n"
                f"파일: {path}\n"
                f"원인: {exc}"
            ) from exc

        if not isinstance(data, dict):
            return None

        return data

    def save_json(
        self,
        key: str,
        payload: dict[str, Any],
    ) -> Path:
        path = self.json_path(key)
        temporary = path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            temporary.replace(path)
        except OSError as exc:
            if temporary.exists():
                temporary.unlink()

            raise CacheManagerError(
                "캐시 파일을 저장하지 못했습니다.\n"
                f"파일: {path}\n"
                f"원인: {exc}"
            ) from exc

        return path
