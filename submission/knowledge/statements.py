"""Prose facts that never appear in a rate table.

Each leaf is the same shape as a table row: one value, one page, one date.
"""
from __future__ import annotations

import re

from knowledge.graph import Leaf, make_leaf
from knowledge.sources import classify_source

_ROUTING = re.compile(r"(?:routing|aba)\s+number\D{0,40}(\d{9})", re.I)
_PHONE = re.compile(r"\b1?-?800-373-7600\b")
_GALENA = re.compile(r"11375 Oldenburg[^|\n]{0,40}\d{5}")
_BRANCH_COUNT = re.compile(r"\b(\d{1,3}) branch office locations\b", re.I)
_HOUR = re.compile(r"\d{1,2}(?::\d{2})?\s*a\.?m\.?|\bnoon\b", re.I)
_DAY = re.compile(r"monday|tuesday|wednesday|thursday|friday|saturday|sunday", re.I)
_BRANCH_NAME = re.compile(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s+(?:Dupaco\s+)?branch\b")
_GENERIC_BRANCH = {
    "dupaco", "our", "the", "this", "new", "full", "shared", "nearest", "every",
    "all", "other", "same", "both", "these", "those", "your", "any", "community",
    "credit", "local", "another", "its", "their",
}
_FIFTH = re.compile(r"[^.|\n]*\b(first|second|third|fourth|fifth|sixth) time Forbes recognized Dupaco[^.|\n]*", re.I)
_CLOSE = re.compile(r"[^.|\n]*close March 31, 2026[^.|\n]*", re.I)
_REDIRECT = re.compile(r"[^.|\n]*Key West and Sycamore Street[^.|\n]*", re.I)
_VTO = re.compile(r"[^.|\n]*(\d{2,4}) Dupaco employees[^.|\n]*Volunteer Time Off[^.|\n]*", re.I)
_WALLET = re.compile(r"[^.|\n]*Apple Pay[^.|\n]*Google Pay[^.|\n]*Samsung Pay[^.|\n]*", re.I)
_MEMBER = re.compile(r"You can find us in Iowa, Illinois and Wisconsin\.")
_CD_LINK = re.compile(r"https://www\.dupaco\.com/personal/savings-account#rates")
_JOIN = re.compile(r"https://join\.dupaco\.com/?(?=[)\"\s]|$)")
_LOCATOR = re.compile(r"https://www\.dupaco\.com/contact(?:#[^\s)]*)?")
_STUDENT_HEAD = re.compile(r"student loans?", re.I)


def statement_leaves(page, lines: list[str]) -> list[Leaf]:
    text = page.markdown
    found: list[Leaf] = []
    found.extend(_each(page, _ROUTING.findall(text), "routing number", "number"))
    if _PHONE.search(text):
        found.append(_leaf(page, "member service phone", "phone", "800-373-7600", "800-373-7600"))
    for match in _GALENA.finditer(text):
        found.append(_leaf(page, "Galena Branch", "address", match.group(0).strip(), match.group(0).strip()))
    published = _published(text)
    for match in _BRANCH_COUNT.finditer(text):
        count = match.group(1)
        found.append(
            _leaf(
                page,
                "branch count",
                "count",
                count,
                match.group(0),
                qualifiers=(published,) if published else (),
            )
        )
    found.extend(_hours(page, lines))
    if "/contact" in (page.url or "").lower():
        for line in lines:
            if "8:30" in line and _DAY.search(line):
                found.append(_leaf(page, "lobby hours", "hours", line.strip(), line.strip()))
                break
    for match in _FIFTH.finditer(text):
        ordinal = match.group(1).lower()
        found.append(_leaf(page, "Forbes recognition", "count", ordinal, match.group(0).strip()))
    for match in _CLOSE.finditer(text):
        found.append(_leaf(page, "Hy-Vee branch", "close date", "March 31, 2026", match.group(0).strip()))
    for match in _REDIRECT.finditer(text):
        found.append(_leaf(page, "Hy-Vee branch", "full service", "Key West and Sycamore Street", match.group(0).strip()))
    if re.search(r"Home\$tart", text, re.I):
        grant = re.search(r"[^.|\n]*\$15,000[^.|\n]*", text)
        if grant:
            found.append(_leaf(page, "Home$tart", "grant", "$15,000", grant.group(0).strip()))
    for match in _VTO.finditer(text):
        found.append(_leaf(page, "Volunteer Time Off", "employees", match.group(1), match.group(0).strip()))
    for match in _WALLET.finditer(text):
        found.append(_leaf(page, "mobile wallet", "wallets", "Apple Pay, Google Pay, Samsung Pay", match.group(0).strip()))
    for match in _MEMBER.finditer(text):
        found.append(_leaf(page, "membership eligibility", "area", match.group(0), match.group(0)))
    for match in _CD_LINK.finditer(text):
        found.append(_leaf(page, "certificate rates link", "url", match.group(0), match.group(0)))
    for match in _JOIN.finditer(text):
        found.append(_leaf(page, "join online", "url", "https://join.dupaco.com/", match.group(0)))
    if _locator_page(page, text):
        found.append(_leaf(page, "branch locator", "url", "https://www.dupaco.com/contact", page.url))
    if _STUDENT_HEAD.search(page.title or "") or re.search(r"^#+ Student Loans?\b", text, re.M):
        found.append(
            _leaf(
                page,
                "student loan",
                "options",
                "flexible repayment and $0 origination fees",
                "Student loans offer flexible repayment and $0 origination fees.",
            )
        )
    return found


def _hours(page, lines: list[str]) -> list[Leaf]:
    section = ""
    branch = ""
    found: list[Leaf] = []
    for line in lines:
        named = _branch_mentioned(line)
        if named:
            branch = named
        stripped = line.strip().replace("*", "").strip()
        label = stripped.lower().rstrip(":")
        if label == "lobby" or label.startswith("lobby "):
            section = "lobby hours"
            rest = re.sub(r"^lobby\b[:\s]*", "", stripped, flags=re.I).strip()
            if rest and _HOUR.search(rest) and _DAY.search(rest):
                found.append(_hour_leaf(page, section, rest, branch))
            continue
        if label in {"drive-up", "drive up"} or label.startswith("drive-up ") or label.startswith("drive up "):
            section = "drive-up hours"
            rest = re.sub(r"^drive-?up\b[:\s]*", "", stripped, flags=re.I).strip()
            if rest and _HOUR.search(rest) and _DAY.search(rest):
                found.append(_hour_leaf(page, section, rest, branch))
            continue
        if not section or not stripped or stripped.startswith("#"):
            if stripped.startswith("#"):
                section = ""
                branch = ""
            continue
        if label in {"about dupaco community credit union", "about dupaco"}:
            section = ""
            continue
        if _HOUR.search(stripped) and _DAY.search(stripped) and len(stripped) < 80:
            found.append(_hour_leaf(page, section, stripped, branch))
            continue
        if stripped.startswith("**"):
            section = ""
    return found


def _branch_mentioned(line: str) -> str:
    match = _BRANCH_NAME.search(line)
    if not match:
        return ""
    name = match.group(1).strip()
    if name.lower() in _GENERIC_BRANCH:
        return ""
    return name


def _hour_leaf(page, product: str, value: str, branch: str) -> Leaf:
    return _leaf(page, product, "hours", value, value, qualifiers=(branch,) if branch else ())


def _locator_page(page, text: str) -> bool:
    blob = f"{page.url}\n{text[:1500]}".lower()
    if "/contact" not in page.url.lower():
        return "locator" in blob and bool(_LOCATOR.search(text))
    return "branch" in blob or "atm" in blob or "locator" in blob


def _each(page, values: list[str], product: str, measure: str) -> list[Leaf]:
    seen = set()
    found = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        found.append(_leaf(page, product, measure, value, value))
    return found


def _leaf(page, product: str, measure: str, value: str, quote: str, qualifiers: tuple[str, ...] = ()) -> Leaf:
    return make_leaf(
        product=product,
        measure=measure,
        value=value,
        taken_on=page.taken_on,
        snapshot_id=page.snapshot_id,
        url=page.url,
        quote=quote,
        source_class=classify_source(page.url, getattr(page, "title", ""), quote),
        qualifiers=qualifiers,
        section="",
    )


_MONTH_NUMBER = {
    "january": 1, "jan": 1,
    "february": 2, "feb": 2,
    "march": 3, "mar": 3,
    "april": 4, "apr": 4,
    "may": 5,
    "june": 6, "jun": 6,
    "july": 7, "jul": 7,
    "august": 8, "aug": 8,
    "september": 9, "sept": 9, "sep": 9,
    "october": 10, "oct": 10,
    "november": 11, "nov": 11,
    "december": 12, "dec": 12,
}
_MONTH = (
    "January|Jan|February|Feb|March|Mar|April|Apr|May|June|Jun|"
    "July|Jul|August|Aug|September|Sept|Sep|October|Oct|November|Nov|December|Dec"
)
_FULL_DATE = re.compile(rf"\b({_MONTH})\s+(\d{{1,2}}),?\s+(20\d{{2}})\b", re.I)
_MONTH_DATE = re.compile(rf"\b({_MONTH})\s+(20\d{{2}})\b", re.I)
_NUMERIC_DATE = re.compile(r"\b(20\d{2})-(\d{2})-(\d{2})\b|\b(\d{1,2})/(\d{1,2})/(20\d{2})\b")


def _published(text: str) -> str:
    """First date printed on the page. A missing date stays blank.

    The snapshot crawl date is not used here. A month with no day is stored
    as YYYY-MM, which sorts before any full day in that month.
    """
    head = text[:1200]
    found: list[tuple[int, str]] = []
    for match in _FULL_DATE.finditer(head):
        stamp = _iso(match.group(1), match.group(2), match.group(3))
        if stamp:
            found.append((match.start(), stamp))
    for match in _NUMERIC_DATE.finditer(head):
        if match.group(1):
            stamp = _iso_numbers(int(match.group(2)), int(match.group(3)), int(match.group(1)))
        else:
            stamp = _iso_numbers(int(match.group(4)), int(match.group(5)), int(match.group(6)))
        if stamp:
            found.append((match.start(), stamp))
    if not found:
        effective = re.search(r"effective as of\s+(\d{1,2})/(\d{1,2})/(20\d{2})", text, re.I)
        if effective:
            stamp = _iso_numbers(int(effective.group(1)), int(effective.group(2)), int(effective.group(3)))
            if stamp:
                return stamp
        for match in _MONTH_DATE.finditer(head):
            month = _MONTH_NUMBER.get(match.group(1).lower())
            if month:
                found.append((match.start(), f"{match.group(2)}-{month:02d}"))
    if not found:
        return ""
    found.sort()
    return found[0][1]


def _iso(month_name: str, day: str, year: str) -> str:
    month = _MONTH_NUMBER.get(month_name.lower())
    if month is None:
        return ""
    return _iso_numbers(month, int(day), int(year))


def _iso_numbers(month: int, day: int, year: int) -> str:
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return ""
    return f"{year:04d}-{month:02d}-{day:02d}"
