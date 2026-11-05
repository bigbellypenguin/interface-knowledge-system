"""Source class, then crawl date, decides which leaf wins."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "submission"))

from knowledge.graph import make_leaf  # noqa: E402
from knowledge.rank import ranked, winner  # noqa: E402


def _leaf(value, taken_on, source_class, url="https://example-cu.test/rates/certificates"):
    return make_leaf(
        product="6-month certificate",
        measure="apy",
        value=value,
        taken_on=taken_on,
        snapshot_id=taken_on,
        url=url,
        quote=value,
        source_class=source_class,
    )


class RankTests(unittest.TestCase):
    def test_rate_sheet_beats_newer_promo(self):
        promo = _leaf("5.00%", "2026-03-01", "promo", "https://example-cu.test/promo")
        rate_sheet = _leaf("3.50%", "2026-01-05", "rate_sheet")
        picked = winner([promo, rate_sheet])
        self.assertEqual(picked.source_class, "rate_sheet")
        self.assertEqual(picked.value, "3.50%")

    def test_newer_taken_on_wins_within_source_class(self):
        older = _leaf("2.95%", "2026-01-05", "rate_sheet", "https://example-cu.test/rates/a")
        newer = _leaf("3.50%", "2026-03-01", "rate_sheet", "https://example-cu.test/rates/b")
        self.assertEqual(winner([older, newer]).value, "3.50%")

    def test_as_of_hides_later_leaf(self):
        january = _leaf("2.95%", "2026-01-05", "rate_sheet")
        march = _leaf("3.50%", "2026-03-01", "product", "https://example-cu.test/personal/certificates")
        picked = winner([march, january], "2026-01-31")
        self.assertEqual(picked.value, "2.95%")
        self.assertEqual(
            [leaf.taken_on for leaf in ranked([march, january], "2026-01-31")],
            ["2026-01-05"],
        )

    def test_empty_input_returns_none(self):
        self.assertIsNone(winner([]))

    def test_unknown_source_class_loses_to_archive(self):
        unknown = _leaf("9.99%", "2026-06-01", "blog", "https://example-cu.test/blog")
        archive = _leaf("1.00%", "2020-01-01", "archive", "https://example-cu.test/2018/09/25/note")
        picked = winner([unknown, archive])
        self.assertEqual(picked.source_class, "archive")
        self.assertEqual(picked.value, "1.00%")


if __name__ == "__main__":
    unittest.main()
