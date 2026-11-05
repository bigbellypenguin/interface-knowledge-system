"""Facts whose leaves disagree, resolved by the same ranker answers use."""
from __future__ import annotations

from contract import Conflict, Source

from knowledge.graph import FactGraph
from knowledge.rank import winner


def find_conflicts(graph: FactGraph) -> list[Conflict]:
    found = []
    for fact_id in graph.fact_ids():
        leaves = graph.leaves_for(fact_id)
        values = list(dict.fromkeys(leaf.value for leaf in leaves))
        if len(values) < 2:
            continue
        chosen = winner(leaves)
        found.append(
            Conflict(
                topic=fact_id,
                values=values,
                sources=[
                    Source(url=leaf.url, snapshot_id=leaf.snapshot_id, quote=leaf.quote)
                    for leaf in leaves
                ],
                resolution=None if chosen is None else chosen.value,
                reason=None
                if chosen is None
                else f"{chosen.source_class} dated {chosen.taken_on} outranks the other leaves",
            )
        )
    return found
