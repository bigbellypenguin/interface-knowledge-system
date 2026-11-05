"""Fact graph.

Layer 1 is the product (does this information exist). Layer 2 is the crawl
date on each leaf. The leaf itself is one value from one page.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_SPACE = re.compile(r"\s+")


def norm(text: str) -> str:
    text = (text or "").lower().replace("–", "-").replace("—", "-")
    return _SPACE.sub(" ", text).strip()


def make_fact_id(product: str, qualifiers: tuple[str, ...] = (), measure: str = "") -> str:
    parts = [norm(product)]
    parts.extend(norm(q) for q in qualifiers if norm(q))
    if norm(measure):
        parts.append(norm(measure))
    return " | ".join(parts)


@dataclass(frozen=True)
class Leaf:
    fact_id: str
    product: str
    qualifiers: tuple[str, ...]
    measure: str
    value: str
    taken_on: str
    snapshot_id: str
    url: str
    quote: str
    source_class: str
    section: str = ""


def make_leaf(
    *,
    product: str,
    measure: str,
    value: str,
    taken_on: str,
    snapshot_id: str,
    url: str,
    quote: str,
    source_class: str,
    qualifiers: tuple[str, ...] = (),
    section: str = "",
) -> Leaf:
    return Leaf(
        fact_id=make_fact_id(product, qualifiers, measure),
        product=product,
        qualifiers=tuple(qualifiers),
        measure=measure,
        value=value.strip(),
        taken_on=taken_on,
        snapshot_id=snapshot_id,
        url=url,
        quote=quote.strip(),
        source_class=source_class,
        section=section,
    )


class FactGraph:
    def __init__(self) -> None:
        self._leaves: list[Leaf] = []
        self._by_fact: dict[str, list[Leaf]] = {}
        self._products: set[str] = set()

    def add(self, leaf: Leaf) -> None:
        self._leaves.append(leaf)
        self._by_fact.setdefault(leaf.fact_id, []).append(leaf)
        self._products.add(leaf.product)

    def __len__(self) -> int:
        return len(self._leaves)

    def products(self) -> set[str]:
        return set(self._products)

    def has_product(self, name: str) -> bool:
        needle = norm(name)
        if not needle:
            return False
        return any(needle == norm(product) or needle in norm(product) for product in self._products)

    def fact_ids(self, as_of: str | None = None) -> list[str]:
        found = []
        for fact_id, leaves in self._by_fact.items():
            if any(_visible(leaf, as_of) for leaf in leaves):
                found.append(fact_id)
        return found

    def leaves_for(self, fact_id: str, as_of: str | None = None) -> list[Leaf]:
        return [leaf for leaf in self._by_fact.get(fact_id, []) if _visible(leaf, as_of)]

    def visible(self, as_of: str | None = None) -> list[Leaf]:
        return [leaf for leaf in self._leaves if _visible(leaf, as_of)]


def _visible(leaf: Leaf, as_of: str | None) -> bool:
    return as_of is None or leaf.taken_on <= as_of
