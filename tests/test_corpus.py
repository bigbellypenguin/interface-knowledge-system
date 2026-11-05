"""Corpus behavior the answer and conflict code will rely on."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "submission"))
sys.path.insert(0, str(KIT / "harness"))

from contract import Page, Snapshot  # noqa: E402
from knowledge.store import Corpus  # noqa: E402


def _snap(sid: str, taken_on: str, pages: list[tuple[str, str]]) -> Snapshot:
    return Snapshot(
        snapshot_id=sid,
        taken_on=taken_on,
        pages=[
            Page(url=url, title=url, markdown=md, fetched_at=taken_on + "T00:00:00Z")
            for url, md in pages
        ],
    )


class CorpusTests(unittest.TestCase):
    def test_current_pages_follow_the_latest_full_snapshot(self):
        corpus = Corpus()
        corpus.ingest(_snap("jan", "2026-01-05", [
            ("https://cu.test/rates", "6-month 2.95%"),
            ("https://cu.test/old-promo", "expired offer"),
        ]))
        corpus.ingest(_snap("mar", "2026-03-01", [
            ("https://cu.test/rates", "6-month 3.50%"),
        ]))

        current = {p.url: p.markdown for p in corpus.current_pages(None)}
        self.assertEqual(current, {"https://cu.test/rates": "6-month 3.50%"})

        january = {p.url: p.markdown for p in corpus.current_pages("2026-01-31")}
        self.assertEqual(january["https://cu.test/rates"], "6-month 2.95%")
        self.assertIn("https://cu.test/old-promo", january)

    def test_as_of_before_any_snapshot_is_empty(self):
        corpus = Corpus()
        corpus.ingest(_snap("jan", "2026-01-05", [("https://cu.test/rates", "2.95%")]))
        self.assertEqual(corpus.current_pages("2025-12-31"), [])

    def test_history_keeps_every_observation_up_to_as_of(self):
        corpus = Corpus()
        corpus.ingest(_snap("jan", "2026-01-05", [("https://cu.test/rates", "2.95%")]))
        corpus.ingest(_snap("mar", "2026-03-01", [("https://cu.test/rates", "3.50%")]))

        self.assertEqual(
            [p.markdown for p in corpus.history("https://cu.test/rates")],
            ["2.95%", "3.50%"],
        )
        self.assertEqual(
            [p.markdown for p in corpus.history("https://cu.test/rates", as_of="2026-01-31")],
            ["2.95%"],
        )
        self.assertEqual(corpus.history("https://cu.test/missing"), [])

    def test_duplicate_url_in_one_snapshot_keeps_the_last_copy(self):
        corpus = Corpus()
        corpus.ingest(_snap("jan", "2026-01-05", [
            ("https://cu.test/rates", "first"),
            ("https://cu.test/rates", "second"),
        ]))
        self.assertEqual(corpus.current_pages(None)[0].markdown, "second")

    def test_ingest_order_is_call_order(self):
        corpus = Corpus()
        corpus.ingest(_snap("mar", "2026-03-01", [("https://cu.test/rates", "later")]))
        corpus.ingest(_snap("jan", "2026-01-05", [("https://cu.test/rates", "earlier")]))
        self.assertEqual(corpus.current_pages(None)[0].markdown, "earlier")
        # March is after this cutoff, so the earlier call is the one that qualifies.
        self.assertEqual(corpus.resolve("2026-02-01").snapshot_id, "jan")


if __name__ == "__main__":
    unittest.main()
