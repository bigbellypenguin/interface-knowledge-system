"""Branch hours, wallet measure, savings rows, and printed dates."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

KIT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(KIT / "submission"))
sys.path.insert(0, str(KIT / "harness"))

from contract import Page, Snapshot  # noqa: E402
from knowledge.statements import _published  # noqa: E402
from solution import build  # noqa: E402

_PLATTEVILLE = """\
The Platteville Dupaco branch is located at 1100 E. Business Highway 151.

Branch hours are:

**Lobby**

Monday-Thursday: 8:30 a.m.–5 p.m.

Saturday: 9 a.m.–noon

**Drive-up**

Monday-Friday: 8 a.m.–6 p.m.
"""

_CEDAR = """\
The Cedar Rapids Dupaco branch is open downtown.

**Lobby**

Monday-Friday: 7:15 a.m.–4 p.m.

Saturday: 8:30 a.m.–12:30 p.m.
"""

_RATES = """\
Share Savings

| Account Type | Balance Tier | Dividend Rate | Annual Percentage Yield (APY) |
| --- | --- | --- | --- |
| Share Savings | $25,000+ | 0.20% | 0.20% |
| Share Savings | $0 – $99.99 | 0.00% | 0.00% |

Investor's Choice Money Market

| Account Type | Balance Tier | Dividend Rate | Annual Percentage Yield (APY) |
| --- | --- | --- | --- |
| Investor's Choice Money Market | $25,000 – $99,999.99 | 0.35% | 0.35% |

Health Savings Account

| Account Type | Balance Tier | Dividend Rate | Annual Percentage Yield (APY) |
| --- | --- | --- | --- |
| Health Savings Account | $25,000+ | 0.35% | 0.35% |

Platinum Visa

| Card Type | APR |
| --- | --- |
| Platinum Visa Rate | 12.50% – 19.50% |
"""

_SHINE = """\
Definitely! You can add your Dupaco debit or credit cards to Apple Pay, Google Pay or Samsung Pay to pay from your phone.
"""


class WordingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ks = build()
        cls.ks.ingest(
            Snapshot(
                snapshot_id="snap",
                taken_on="2026-09-28",
                pages=[
                    Page("https://www.dupaco.com/newsroom/platteville", "Platteville", _PLATTEVILLE, "2026-09-28"),
                    Page("https://www.dupaco.com/newsroom/cedar", "Cedar Rapids", _CEDAR, "2026-09-28"),
                    Page("https://www.dupaco.com/rates", "Rates", _RATES, "2026-09-28"),
                    Page("https://www.dupaco.com/shine", "Shine", _SHINE, "2026-09-28"),
                ],
            )
        )

    def test_platteville_hours_are_that_branch_only(self):
        answer = self.ks.answer("What are the hours at the Platteville branch?")
        self.assertTrue(answer.confident)
        self.assertIn("Platteville", answer.text)
        self.assertIn("noon", answer.text.lower())
        self.assertIn("8 a.m.", answer.text)
        self.assertNotIn("7:15", answer.text)
        self.assertNotIn("12:30", answer.text)

    def test_unknown_branch_hours_refuse(self):
        answer = self.ks.answer("Can you give me the lobby hours for the Mullan Avenue branch?")
        self.assertFalse(answer.confident)
        self.assertEqual(answer.text, "I don't know.")

    def test_all_branches_still_lists_both_saturday_schedules(self):
        answer = self.ks.answer("Do all Dupaco branches keep the same lobby hours?")
        self.assertIn("12:30", answer.text)
        self.assertIn("noon", answer.text.lower())

    def test_visa_on_a_phone_is_the_wallet(self):
        answer = self.ks.answer("Can I put my Visa on my phone?")
        self.assertIn("Apple Pay", answer.text)
        self.assertIn("Google Pay", answer.text)
        self.assertIn("Samsung Pay", answer.text)
        self.assertNotIn("12.50", answer.text)

    def test_platinum_apr_is_still_the_card_rate(self):
        answer = self.ks.answer("What is the standard purchase APR on the Dupaco Platinum Visa?")
        self.assertIn("12.50", answer.text)
        self.assertNotIn("Apple Pay", answer.text)

    def test_savings_035_reads_every_matching_row(self):
        answer = self.ks.answer("Do any Dupaco savings tiers pay 0.35% APY?")
        self.assertIn("0.20", answer.text)
        self.assertIn("0.35", answer.text)
        self.assertIn("Investor's Choice", answer.text)
        self.assertIn("Health Savings", answer.text)
        self.assertNotIn("up to 0.35", answer.text.lower())


class PrintedDateTests(unittest.TestCase):
    def test_abbreviated_month_and_month_only(self):
        self.assertEqual(_published("Written by Emily Kittle | Oct 8, 2021 12:57:34 PM"), "2021-10-08")
        self.assertEqual(_published("October 8, 2021"), "2021-10-08")
        self.assertEqual(_published("The report was updated March 2026 and no day was given."), "2026-03")
        self.assertEqual(_published("Rates are effective as of 09/01/2026."), "2026-09-01")
        self.assertEqual(_published("No calendar date appears here."), "")
        self.assertLess("2026-03", "2026-03-17")
        self.assertLess("2026-03-17", "2026-05-05")

    def test_same_day_disagreement_names_both_values(self):
        ks = build()
        ks.ingest(
            Snapshot(
                snapshot_id="snap",
                taken_on="2026-09-28",
                pages=[
                    Page(
                        "https://www.dupaco.com/newsroom/one",
                        "One",
                        "May 5, 2026\n\nIt has over 600 employees and 22 branch office locations.",
                        "2026-09-28",
                    ),
                    Page(
                        "https://www.dupaco.com/newsroom/two",
                        "Two",
                        "May 5, 2026\n\nIt has over 600 employees and 23 branch office locations.",
                        "2026-09-28",
                    ),
                ],
            )
        )
        answer = ks.answer("How many branches does Dupaco have?")
        self.assertIn("22", answer.text)
        self.assertIn("23", answer.text)
        self.assertIn("disagree", answer.text)
        self.assertEqual(answer.conflict_note, "same article date and source class")


if __name__ == "__main__":
    unittest.main()
