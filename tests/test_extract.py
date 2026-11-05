"""Tables and labeled lines become one leaf per value."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "submission"))

from knowledge.extract import extract_page  # noqa: E402


def _page(url, markdown, title=""):
    return SimpleNamespace(
        url=url,
        title=title,
        markdown=markdown,
        snapshot_id="snap",
        taken_on="2026-01-05",
    )


class ExtractTests(unittest.TestCase):
    def test_certificate_apy_line_is_rate_sheet(self):
        line = "6-month certificate APY: 2.95%"
        leaves = extract_page(_page("https://example-cu.test/rates/certificates", line, "Certificates"))

        self.assertEqual(len(leaves), 1)
        leaf = leaves[0]
        self.assertEqual(leaf.product, "6-month certificate")
        self.assertEqual(leaf.measure, "APY")
        self.assertEqual(leaf.value, "2.95%")
        self.assertEqual(leaf.source_class, "rate_sheet")
        self.assertEqual(leaf.quote, line)

    def test_replacement_fee_line_is_product(self):
        line = "Lost debit card replacement fee: $2.50"
        leaves = extract_page(_page("https://example-cu.test/fees", line, "Fees"))

        self.assertEqual(len(leaves), 1)
        leaf = leaves[0]
        self.assertEqual(leaf.product, "Lost debit card replacement")
        self.assertEqual(leaf.measure, "fee")
        self.assertEqual(leaf.value, "$2.50")
        self.assertEqual(leaf.source_class, "product")

    def test_expired_offer_line_is_promo(self):
        line = "Summer special: 6-month certificate APY 2.95% (offer ended 2025-09-30)"
        leaves = extract_page(_page("https://example-cu.test/promo", line, "Promo"))

        self.assertEqual(len(leaves), 1)
        leaf = leaves[0]
        self.assertEqual(leaf.value, "2.95%")
        self.assertEqual(leaf.measure, "APY")
        self.assertEqual(leaf.source_class, "promo")
        self.assertIn("6-month certificate", leaf.product)
        self.assertIn("offer ended", leaf.quote)

    def test_table_apy_is_not_the_dividend_rate(self):
        markdown = """\
Special Certificates

| Certificate | Dividend Rate | Annual Percentage Yield (APY) | Min. to Earn |
| --- | --- | --- | --- |
| 17 Month Fixed Jumbo Certificate Special | 4.15% | 4.20%1 | $100,000.00 |
| 17 Month Fixed Certificate Special | 4.06% | 4.10%2 | $1,000.00 |
"""
        leaves = extract_page(_page("https://www.dupaco.com/rates", markdown, "Rates"))
        apy = [leaf for leaf in leaves if "apy" in leaf.measure.lower()]
        jumbo = [leaf for leaf in apy if "jumbo" in leaf.product.lower()]
        regular = [leaf for leaf in apy if "jumbo" not in leaf.product.lower()]

        self.assertEqual([leaf.value for leaf in jumbo], ["4.20%"])
        self.assertEqual([leaf.value for leaf in regular], ["4.10%"])
        self.assertTrue(all(leaf.source_class == "rate_sheet" for leaf in apy))
        self.assertIn("4.20%1", jumbo[0].quote)
        self.assertIn("Special Certificates", jumbo[0].qualifiers)
        self.assertEqual(jumbo[0].section, "Special Certificates")

        dividends = [leaf.value for leaf in leaves if "dividend" in leaf.measure.lower()]
        self.assertEqual(dividends, ["4.15%", "4.06%"])
        minimums = [leaf.value for leaf in leaves if "earn" in leaf.measure.lower()]
        self.assertEqual(minimums, ["$100,000.00", "$1,000.00"])

    def test_payment_example_column_is_skipped(self):
        markdown = """\
Home Loans

| Program | Rate | APR | *Payment Example |
| --- | --- | --- | --- |
| Purchase: 30-Year Fixed | 7.25% | 7.29% | $5,680.83 |
"""
        leaves = extract_page(_page("https://www.dupaco.com/rates", markdown, "Rates"))
        values = [leaf.value for leaf in leaves]
        self.assertIn("7.25%", values)
        self.assertIn("7.29%", values)
        self.assertNotIn("$5,680.83", values)

    def test_balance_tier_qualifies_the_rate(self):
        markdown = """\
Share Savings

| Account Type | Balance Tier | Dividend Rate | Annual Percentage Yield (APY) | Min. to Earn |
| --- | --- | --- | --- | --- |
| Share Savings | $25,000+ | 0.20% | 0.20%1 | $25,000.00 |
| Share Savings | $10,000 – $24,999.99 | 0.15% | 0.15%1 | $10,000.00 |
"""
        leaves = extract_page(_page("https://www.dupaco.com/rates", markdown, "Rates"))
        apy = [leaf for leaf in leaves if "apy" in leaf.measure.lower()]
        self.assertEqual([leaf.value for leaf in apy], ["0.20%", "0.15%"])
        self.assertEqual(apy[0].qualifiers, ("Share Savings", "$25,000+"))
        self.assertEqual(apy[1].qualifiers, ("Share Savings", "$10,000 – $24,999.99"))
        self.assertNotIn("$25,000", [leaf.value for leaf in leaves])


if __name__ == "__main__":
    unittest.main()
