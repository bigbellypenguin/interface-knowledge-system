from __future__ import annotations

from knowledge.answer import answer_question
from knowledge.conflicts import find_conflicts
from knowledge.extract import extract_page
from knowledge.graph import FactGraph
from knowledge.store import Corpus


class Knowledge:
    def __init__(self) -> None:
        self.corpus = Corpus()
        self.graph = FactGraph()

    def ingest(self, snapshot) -> None:
        self.corpus.ingest(snapshot)
        for page in self.corpus.snapshots[-1].pages.values():
            for leaf in extract_page(page):
                self.graph.add(leaf)

    def answer(self, question: str, as_of: str | None = None):
        return answer_question(self.graph, question, as_of)

    def conflicts(self):
        return find_conflicts(self.graph)
