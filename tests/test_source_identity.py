from __future__ import annotations

import unittest

from projects.research.source_identity import source_identities


class SourceIdentityTests(unittest.TestCase):
    def test_distinct_doi_urls_are_distinct_academic_works(self) -> None:
        sources = [
            {
                "source_url": f"https://doi.org/10.1000/work-{index}",
                "source_tier": "academic",
            }
            for index in range(2)
        ]

        self.assertEqual(2, len(source_identities(sources)))

    def test_regular_pages_still_share_their_publisher_domain(self) -> None:
        sources = [
            {
                "source_url": f"https://example.com/article-{index}",
                "source_tier": "news",
            }
            for index in range(2)
        ]

        self.assertEqual(1, len(source_identities(sources)))


if __name__ == "__main__":
    unittest.main()
