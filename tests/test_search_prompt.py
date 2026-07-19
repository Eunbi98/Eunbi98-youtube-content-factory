from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DIRECTOR_DIR = ROOT_DIR / "projects" / "director"
if str(DIRECTOR_DIR) not in sys.path:
    sys.path.insert(0, str(DIRECTOR_DIR))

from search_prompt import (  # noqa: E402
    build_scene_search_prompt,
    extract_alias_queries,
)


class SearchPromptTests(unittest.TestCase):
    def test_long_compound_alias_suppresses_nested_short_alias(self) -> None:
        queries = extract_alias_queries("화성에 거대한 벌집이 나타났습니다")

        self.assertIn("honeycomb pattern", queries)
        self.assertNotIn("honey bee", queries)
        self.assertNotIn("beehive close up", queries)

    def test_standalone_short_alias_is_preserved(self) -> None:
        queries = extract_alias_queries("꽃 위의 벌")

        self.assertIn("honey bee", queries)

    def test_voynich_alias_builds_subject_specific_query(self) -> None:
        prompt = build_scene_search_prompt(
            scene_id="scene_003",
            title="Story",
            narration="보이니치 문서의 그림은 여전히 수수께끼입니다.",
            keywords=("보이니치 문서 그림",),
        )

        self.assertTrue(
            prompt.primary_query.startswith("Voynich manuscript")
        )
        self.assertNotIn(
            "Story",
            [query.query for query in prompt.queries],
        )


if __name__ == "__main__":
    unittest.main()
