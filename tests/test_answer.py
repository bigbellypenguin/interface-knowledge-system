"""Ingest the harness fixture and answer from the ranked leaf."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "submission"))
sys.path.insert(0, str(KIT / "harness"))

from run_eval import load_snapshots  # noqa: E402
from solution import build  # noqa: E402


class AnswerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = build()
        for snap in load_snapshots(KIT / "harness" / "selftest" / "snapshots"):
            cls.ks.ingest(snap)

    def test_current_certificate_beats_the_old_rate_and_the_promo(self):
        answer = self.ks.answer("What is the 6-month certificate APY?")
        self.assertIn("3.50%", answer.text)
        self.assertNotIn("2.95%", answer.text)
        self.assertTrue(answer.confident)

    def test_as_of_january_returns_the_earlier_rate(self):
        answer = self.ks.answer("What is the 6-month certificate APY?", as_of="2026-01-31")
        self.assertIn("2.95%", answer.text)
        self.assertNotIn("3.50%", answer.text)

    def test_paraphrase_hits_the_same_fact(self):
        answer = self.ks.answer("Current APY on a six month share certificate?")
        self.assertIn("3.50%", answer.text)

    def test_fee_and_unknown_term(self):
        fee = self.ks.answer("How much is a lost debit card replacement?")
        self.assertIn("$2.50", fee.text)
        unknown = self.ks.answer("What is the 60-month jumbo certificate rate?")
        self.assertFalse(unknown.confident)
        self.assertEqual(unknown.text, "I don't know.")

    def test_conflict_picks_the_current_rate_sheet(self):
        conflicts = self.ks.conflicts()
        self.assertTrue(conflicts)
        match = [c for c in conflicts if "6-month" in c.topic and "2.95%" in c.values and "3.50%" in c.values]
        self.assertEqual(len(match), 1)
        self.assertEqual(match[0].resolution, "3.50%")


if __name__ == "__main__":
    unittest.main()
