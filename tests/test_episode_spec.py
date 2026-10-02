from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DIRECTOR_DIR = ROOT_DIR / "projects" / "director"

if str(DIRECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(DIRECTOR_DIR))

from director import Director, DirectorError  # noqa: E402
from episode_spec import EpisodeSpecError, load_episode_spec  # noqa: E402


def _valid_payload(episode_id: str = "ep014") -> dict:
    return {
        "version": "1.0",
        "episodeId": episode_id,
        "title": "테스트 에피소드",
        "scenes": [
            {
                "type": "hook",
                "title": "훅",
                "narration": "첫 번째 테스트 문장입니다.",
                "keywords": ["test hook image"],
            },
            {
                "type": "ending",
                "title": "마무리",
                "narration": "마지막 테스트 문장입니다.",
                "keywords": ["test ending image"],
            },
        ],
    }


class EpisodeSpecTests(unittest.TestCase):
    def _write_spec(self, directory: Path, payload: dict) -> Path:
        spec_path = directory / "episode.json"
        spec_path.write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )
        return spec_path

    def test_narration_is_always_used_as_subtitle(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = self._write_spec(
                Path(temp_dir),
                _valid_payload(),
            )
            story = load_episode_spec(
                spec_path,
                expected_episode_id="ep014",
            )

        self.assertEqual(2, len(story.beats))
        for beat in story.beats:
            self.assertEqual(beat.narration, beat.subtitle)
        self.assertEqual(
            "ep014/scene_001.jpg",
            story.beats[0].media.src,
        )

    def test_episode_id_mismatch_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = self._write_spec(
                Path(temp_dir),
                _valid_payload("ep999"),
            )
            with self.assertRaises(EpisodeSpecError):
                load_episode_spec(
                    spec_path,
                    expected_episode_id="ep014",
                )

    def test_invalid_first_scene_is_rejected(self) -> None:
        payload = _valid_payload()
        payload["scenes"][0]["type"] = "fact"

        with tempfile.TemporaryDirectory() as temp_dir:
            spec_path = self._write_spec(
                Path(temp_dir),
                payload,
            )
            with self.assertRaises(EpisodeSpecError):
                load_episode_spec(spec_path)

    def test_director_builds_unregistered_episode_from_spec(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            episode_dir = Path(temp_dir) / "ep014"
            episode_dir.mkdir()
            self._write_spec(
                episode_dir,
                _valid_payload(),
            )
            output_path = episode_dir / "timeline.json"

            result = Director().build(
                episode_id="ep014",
                output_path=output_path,
            )

            self.assertTrue(output_path.exists())
            self.assertEqual(2, result.scene_count)

    def test_missing_spec_keeps_clear_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = (
                Path(temp_dir)
                / "ep999"
                / "timeline.json"
            )

            with self.assertRaises(DirectorError) as context:
                Director().build(
                    episode_id="ep999",
                    output_path=output_path,
                )

        self.assertIn("episode.json", str(context.exception))


if __name__ == "__main__":
    unittest.main()
