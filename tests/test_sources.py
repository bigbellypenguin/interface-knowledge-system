"""Source class decides which page is allowed to win."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "submission"))

from knowledge.sources import SOURCE_RANK, classify_source  # noqa: E402


class SourceTests(unittest.TestCase):
    def test_rate_sheet_beats_promo_and_archive(self):
        self.assertGreater(SOURCE_RANK["rate_sheet"], SOURCE_RANK["product"])
        self.assertGreater(SOURCE_RANK["product"], SOURCE_RANK["news"])
        self.assertGreater(SOURCE_RANK["news"], SOURCE_RANK["promo"])
        self.assertGreater(SOURCE_RANK["promo"], SOURCE_RANK["archive"])

    def test_known_urls(self):
        cases = {
            "https://www.dupaco.com/rates": "rate_sheet",
            "https://example-cu.test/rates/certificates": "rate_sheet",
            "https://www.dupaco.com/personal/loans/home-loans": "product",
            "https://www.dupaco.com/business/credit-cards": "product",
            "https://example-cu.test/fees": "product",
            "https://www.dupaco.com/contact": "reference",
            "https://www.dupaco.com/newsroom/forbes-ranks-dupaco": "news",
            "https://example-cu.test/promo": "promo",
            "https://www.dupaco.com/switch-and-earn": "promo",
            "https://www.dupaco.com/2018/09/25/understand-insurance-deductibles/": "archive",
            "https://www.dupaco.com/homebuying-guidance": "archive",
        }
        for url, expected in cases.items():
            self.assertEqual(classify_source(url), expected, url)

    def test_expired_offer_is_promo_even_on_a_product_url(self):
        url = "https://www.dupaco.com/personal/savings-account"
        text = "Summer special: 6-month certificate APY 2.95% (offer ended 2025-09-30)"
        self.assertEqual(classify_source(url, text=text), "promo")


if __name__ == "__main__":
    unittest.main()
