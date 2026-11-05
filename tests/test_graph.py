"""Layer 1 is the product. Layer 2 is the crawl date on each leaf."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "submission"))

from knowledge.graph import FactGraph, make_fact_id, make_leaf  # noqa: E402


def _leaf(product, measure, value, taken_on, **kwargs):
    return make_leaf(
        product=product,
        measure=measure,
        value=value,
        taken_on=taken_on,
        snapshot_id=kwargs.pop("snapshot_id", taken_on),
        url=kwargs.pop("url", "https://example-cu.test/rates/certificates"),
        quote=kwargs.pop("quote", value),
        source_class=kwargs.pop("source_class", "rate_sheet"),
        qualifiers=kwargs.pop("qualifiers", ()),
        **kwargs,
    )


class GraphTests(unittest.TestCase):
    def test_fact_id_includes_qualifiers_and_measure(self):
        plain = make_fact_id("17 month certificate", (), "apy")
        jumbo = make_fact_id("17 month certificate", ("jumbo",), "apy")
        rate = make_fact_id("17 month certificate", (), "dividend rate")
        self.assertNotEqual(plain, jumbo)
        self.assertNotEqual(plain, rate)
        self.assertEqual(plain, make_fact_id("17  Month Certificate", (), "APY"))

    def test_missing_product_is_unknown(self):
        graph = FactGraph()
        graph.add(_leaf("6-month certificate", "apy", "3.50%", "2026-03-01"))
        self.assertTrue(graph.has_product("6-month certificate"))
        self.assertFalse(graph.has_product("60-month jumbo certificate"))

    def test_as_of_hides_later_leaves(self):
        graph = FactGraph()
        graph.add(_leaf("6-month certificate", "apy", "2.95%", "2026-01-05"))
        graph.add(_leaf("6-month certificate", "apy", "3.50%", "2026-03-01"))
        fact_id = make_fact_id("6-month certificate", (), "apy")

        january = graph.leaves_for(fact_id, "2026-01-31")
        self.assertEqual([leaf.value for leaf in january], ["2.95%"])

        current = graph.leaves_for(fact_id, None)
        self.assertEqual([leaf.value for leaf in current], ["2.95%", "3.50%"])
        self.assertNotIn(fact_id, graph.fact_ids("2025-12-31"))


if __name__ == "__main__":
    unittest.main()
