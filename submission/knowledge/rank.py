"""Pick the leaf that is allowed to win.

Higher source class beats a newer crawl. Within one class, the newer crawl wins.
"""
from __future__ import annotations

from knowledge.graph import Leaf
from knowledge.sources import SOURCE_RANK


def ranked(leaves: list[Leaf], as_of: str | None = None) -> list[Leaf]:
    """Leaves visible on as_of (taken_on <= as_of; None means all), best first.

    Order: higher SOURCE_RANK, then newer taken_on, then url.
    Unknown source_class ranks as 0.
    """
    visible = [leaf for leaf in leaves if as_of is None or leaf.taken_on <= as_of]
    ordered = sorted(visible, key=lambda leaf: leaf.url)
    ordered = sorted(ordered, key=lambda leaf: leaf.taken_on, reverse=True)
    ordered = sorted(
        ordered,
        key=lambda leaf: SOURCE_RANK.get(leaf.source_class, 0),
        reverse=True,
    )
    return ordered


def winner(leaves: list[Leaf], as_of: str | None = None) -> Leaf | None:
    """First leaf from ranked(), or None."""
    found = ranked(leaves, as_of)
    return found[0] if found else None
