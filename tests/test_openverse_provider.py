from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
MEDIA_DIR = ROOT_DIR / "projects" / "media"
PROVIDERS_DIR = MEDIA_DIR / "providers"
if str(MEDIA_DIR) not in sys.path:
    sys.path.insert(0, str(MEDIA_DIR))
if str(PROVIDERS_DIR) not in sys.path:
    sys.path.insert(0, str(PROVIDERS_DIR))

try:
    import requests  # noqa: F401
except ModuleNotFoundError:
    class _Session:
        def __init__(self) -> None:
            self.headers: dict[str, str] = {}

    sys.modules["requests"] = types.SimpleNamespace(
        Session=_Session,
        RequestException=Exception,
    )

from openverse_provider import OpenverseProvider  # noqa: E402


class OpenverseProviderTests(unittest.TestCase):
    def test_noncommercial_license_is_rejected(self) -> None:
        candidate = OpenverseProvider()._parse_result(
            raw_result={
                "id": "sample",
                "url": "https://example.com/sample.jpg",
                "width": 1080,
                "height": 1920,
                "title": "Sample",
                "license": "by-nc-sa",
            },
            query="sample",
            min_width=640,
            min_height=480,
        )

        self.assertIsNone(candidate)


if __name__ == "__main__":
    unittest.main()
