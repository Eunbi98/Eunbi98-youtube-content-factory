from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import Mock, patch


ROOT_DIR = Path(__file__).resolve().parents[1]
MEDIA_DIR = ROOT_DIR / "projects" / "media"
PROVIDERS_DIR = MEDIA_DIR / "providers"
for module_path in (ROOT_DIR, MEDIA_DIR, PROVIDERS_DIR):
    if str(module_path) not in sys.path:
        sys.path.insert(0, str(module_path))

from downloader import MediaDownloadError  # noqa: E402
from media_collector import MediaCollector  # noqa: E402
from provider_models import MediaCandidate  # noqa: E402


def candidate(*, media_id: str, query: str) -> MediaCandidate:
    return MediaCandidate(
        provider="openverse",
        media_id=media_id,
        title=f"Image {media_id}",
        query=query,
        media_type="image",
        mime_type="image/jpeg",
        description="ancient artifact",
        source_url=f"https://example.com/source/{media_id}",
        download_url=f"https://example.com/image/{media_id}.jpg",
        thumbnail_url=None,
        author="Tester",
        author_url=None,
        license_name="CC BY 4.0",
        license_url="https://creativecommons.org/licenses/by/4.0/",
        width=1200,
        height=1200,
        orientation="square",
        file_extension=".jpg",
        score=10.0,
    )


class MediaCollectorDownloadRecoveryTest(unittest.TestCase):
    def test_searches_fresh_relaxed_candidates_after_download_failures(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            episode_dir = Path(temporary) / "ep999"
            episode_dir.mkdir(parents=True)
            (episode_dir / "media_queries.json").write_text(
                json.dumps(
                    {
                        "scenes": [
                            {
                                "sceneId": "scene_001",
                                "primaryQuery": "ancient bronze device closeup",
                                "queries": [
                                    {"query": "ancient bronze device closeup"}
                                ],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            collector = MediaCollector.__new__(MediaCollector)
            collector.episode_id = "ep999"
            collector.episode_dir = episode_dir
            collector.query_path = episode_dir / "media_queries.json"
            collector.assets_dir = episode_dir / "assets"
            collector.pixabay = None
            collector.cache = Mock()
            collector.downloader = Mock()

            stale = candidate(
                media_id="stale",
                query="ancient bronze device closeup",
            )
            fresh = replace(
                candidate(media_id="fresh", query="ancient bronze device"),
                provider="wikimedia",
            )
            search_calls: list[dict] = []

            def fake_search(**kwargs):
                search_calls.append(kwargs)
                if kwargs.get("bypass_cache"):
                    return [fresh]
                return [stale]

            def fake_download(*, candidate, destination_dir, scene_id):
                if candidate.media_id == "stale":
                    raise MediaDownloadError("403 expired URL")
                destination_dir.mkdir(parents=True, exist_ok=True)
                output = destination_dir / f"{scene_id}.jpg"
                output.write_bytes(b"fresh-image")
                return output

            collector._search_provider = fake_search
            collector.downloader.download.side_effect = fake_download
            collector.downloader.file_sha256.return_value = "abc123"

            with patch(
                "media_collector.ManifestBuilder.save",
                return_value=episode_dir / "media_manifest_v7.json",
            ):
                result = collector.collect()

            self.assertEqual(
                episode_dir / "media_manifest_v7.json",
                result,
            )
            self.assertTrue(
                any(
                    call.get("bypass_cache") and call.get("relaxed")
                    for call in search_calls
                )
            )
            self.assertTrue((collector.assets_dir / "scene_001.jpg").exists())


if __name__ == "__main__":
    unittest.main()
