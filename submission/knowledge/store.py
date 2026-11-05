"""Crawl history.

Each snapshot is the full site as of that day. `current_pages` returns one
snapshot: the latest whose `taken_on` is on or before `as_of` (or the newest
snapshot when `as_of` is None). `history` keeps every observation of a URL so
later answer and conflict code can see what changed.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PageRecord:
    snapshot_id: str
    taken_on: str
    url: str
    title: str
    markdown: str
    fetched_at: str


@dataclass
class SnapshotRecord:
    snapshot_id: str
    taken_on: str
    pages: dict[str, PageRecord]


class Corpus:
    def __init__(self) -> None:
        self.snapshots: list[SnapshotRecord] = []

    def ingest(self, snapshot) -> None:
        pages: dict[str, PageRecord] = {}
        for page in snapshot.pages:
            pages[page.url] = PageRecord(
                snapshot_id=snapshot.snapshot_id,
                taken_on=snapshot.taken_on,
                url=page.url,
                title=page.title,
                markdown=page.markdown,
                fetched_at=page.fetched_at,
            )
        self.snapshots.append(SnapshotRecord(snapshot.snapshot_id, snapshot.taken_on, pages))

    def resolve(self, as_of: str | None) -> SnapshotRecord | None:
        chosen = None
        for snap in self.snapshots:
            if as_of is None or snap.taken_on <= as_of:
                chosen = snap
        return chosen

    def current_pages(self, as_of: str | None) -> list[PageRecord]:
        snap = self.resolve(as_of)
        if snap is None:
            return []
        return list(snap.pages.values())

    def history(self, url: str, as_of: str | None = None) -> list[PageRecord]:
        found = []
        for snap in self.snapshots:
            if as_of is not None and snap.taken_on > as_of:
                continue
            page = snap.pages.get(url)
            if page is not None:
                found.append(page)
        return found
