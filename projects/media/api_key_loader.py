from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class ApiKeyLoaderError(RuntimeError):
    pass


def load_api_keys(project_root: Path) -> dict[str, str]:
    keys = {
        "pixabay": os.getenv("PIXABAY_API_KEY", "").strip(),
        "pexels": os.getenv("PEXELS_API_KEY", "").strip(),
    }

    config_path = (
        project_root
        / "config"
        / "api_keys.json"
    )

    if config_path.exists():
        try:
            raw_data: Any = json.loads(
                config_path.read_text(
                    encoding="utf-8"
                )
            )
        except (
            OSError,
            json.JSONDecodeError,
        ) as exc:
            raise ApiKeyLoaderError(
                "API 키 설정 파일을 읽지 못했습니다.\n"
                f"파일: {config_path}\n"
                f"원인: {exc}"
            ) from exc

        if not isinstance(raw_data, dict):
            raise ApiKeyLoaderError(
                "config/api_keys.json의 "
                "최상위 값은 객체여야 합니다."
            )

        for provider_name in (
            "pixabay",
            "pexels",
        ):
            if keys[provider_name]:
                continue

            raw_value = raw_data.get(
                provider_name
            )

            if isinstance(raw_value, str):
                keys[provider_name] = (
                    raw_value.strip()
                )

    return keys
