"""Turn one crawled page into fact leaves."""
from __future__ import annotations

import re

from knowledge.graph import Leaf, make_leaf
from knowledge.sources import classify_source
from knowledge.statements import statement_leaves

_PERCENT = re.compile(r"\d+(?:\.\d+)?%")
_DOLLAR = re.compile(r"\$\d[\d,]*(?:\.\d+)?")
_SEP_CELL = re.compile(r":?-{3,}:?")
_HEADING = re.compile(r"^#+\s*")
_TRAILING_MEASURE = re.compile(r"\s+(APY|fee)\s*$", re.I)
_BARE_NUMBER = re.compile(r"-?\d+(?:\.\d+)?")
_FOOTNOTE_LINE = re.compile(r"^\d{1,2}[A-Za-z]")
_AFTER_VALUE = re.compile(r"\d*(?:\s*\([^)]{0,120}\))?")
_PLACEHOLDERS = {"—", "-", "–", "--", "n/a", "N/A", "na", "NA"}


def extract_page(page) -> list[Leaf]:
    """Turn one crawled page into fact leaves.

    page has: url, title, markdown, snapshot_id, taken_on.
    """
    lines = page.markdown.splitlines()
    leaves: list[Leaf] = []
    index = 0
    while index < len(lines):
        if _table_starts(lines, index):
            table_leaves, index = _table_leaves(page, lines, index)
            leaves.extend(table_leaves)
            continue
        leaf = _labeled_leaf(page, lines[index])
        if leaf is not None:
            leaves.append(leaf)
        index += 1
    leaves.extend(statement_leaves(page, lines))
    return leaves


def _table_starts(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines):
        return False
    header = _cells(lines[index])
    separator = _cells(lines[index + 1])
    if header is None or separator is None:
        return False
    return not _is_separator(header) and _is_separator(separator)


def _table_leaves(page, lines: list[str], header_index: int) -> tuple[list[Leaf], int]:
    headers = _cells(lines[header_index]) or []
    section = _section_above(lines, header_index)
    leaves: list[Leaf] = []
    index = header_index + 2
    while index < len(lines):
        cells = _cells(lines[index])
        if cells is None or _is_separator(cells):
            break
        leaves.extend(_row_leaves(page, lines[index], headers, cells, section))
        index += 1
    return leaves, index


def _row_leaves(page, raw_line: str, headers: list[str], cells: list[str], section: str) -> list[Leaf]:
    product = cells[0].strip() if cells else ""
    if not product:
        return []
    quote = raw_line.strip()
    source_class = classify_source(page.url, page.title, quote)
    qualifiers = _qualifiers(section, headers, cells)
    leaves: list[Leaf] = []
    for index, header in enumerate(headers):
        if index == 0 or index >= len(cells) or _skip_header(header):
            continue
        value = _cell_value(cells[index])
        if value is None:
            continue
        leaves.append(
            make_leaf(
                product=product,
                measure=_measure_name(header),
                value=value,
                taken_on=page.taken_on,
                snapshot_id=page.snapshot_id,
                url=page.url,
                quote=quote,
                source_class=source_class,
                qualifiers=qualifiers,
                section=section,
            )
        )
    return leaves


def _qualifiers(section: str, headers: list[str], cells: list[str]) -> tuple[str, ...]:
    quals: list[str] = []
    if section:
        quals.append(section)
    for index, cell in enumerate(cells):
        if index == 0:
            continue
        header = headers[index] if index < len(headers) else ""
        if _skip_header(header):
            continue
        text = cell.strip()
        if not text or text in _PLACEHOLDERS or _BARE_NUMBER.fullmatch(text):
            continue
        if _cell_value(text) is not None:
            continue
        quals.append(text)
    return tuple(quals)


def _labeled_leaf(page, line: str) -> Leaf | None:
    raw = line.strip()
    if not raw or raw.startswith("|") or raw.startswith("#") or ":" not in raw:
        return None
    if _FOOTNOTE_LINE.match(raw):
        return None
    value = _line_value(raw)
    if value is None or raw.find(value) < raw.find(":"):
        return None
    after = raw.split(value, 1)[1].strip()
    if not _AFTER_VALUE.fullmatch(after):
        return None
    product, measure = _label(raw, value)
    if not product:
        return None
    return make_leaf(
        product=product,
        measure=measure,
        value=value,
        taken_on=page.taken_on,
        snapshot_id=page.snapshot_id,
        url=page.url,
        quote=raw,
        source_class=classify_source(page.url, page.title, raw),
        qualifiers=(),
        section="",
    )


def _label(line: str, value: str) -> tuple[str, str]:
    before = re.sub(r"[\s:]+$", "", line.split(value, 1)[0].strip())
    if re.search(r"\bAPY\b", line, re.I):
        measure = "APY"
    elif re.search(r"\bfee\b", line, re.I):
        measure = "fee"
    else:
        measure = ""
    if measure:
        trimmed = re.sub(r"[\s:]+$", "", _TRAILING_MEASURE.sub("", before).strip())
        if trimmed:
            before = trimmed
    return before, measure


def _line_value(line: str) -> str | None:
    percents = _PERCENT.findall(line)
    dollars = _DOLLAR.findall(line)
    if re.search(r"\bAPY\b", line, re.I) and percents:
        return percents[0]
    if re.search(r"\bfee\b", line, re.I) and dollars:
        return dollars[0]
    if len(percents) + len(dollars) == 1:
        return percents[0] if percents else dollars[0]
    return None


def _section_above(lines: list[str], header_index: int) -> str:
    for index in range(header_index - 1, -1, -1):
        text = lines[index].strip()
        if not text or text.startswith("|"):
            continue
        return _HEADING.sub("", text).strip()
    return ""


def _cells(line: str) -> list[str] | None:
    raw = line.strip()
    if not raw.startswith("|"):
        return None
    if raw.endswith("|"):
        raw = raw[:-1]
    return [cell.strip() for cell in raw[1:].split("|")]


def _is_separator(cells: list[str]) -> bool:
    return len(cells) >= 2 and all(_SEP_CELL.fullmatch(cell.replace(" ", "")) for cell in cells)


def _skip_header(header: str) -> bool:
    text = header.lower()
    return "payment" in text or "example" in text


def _measure_name(header: str) -> str:
    name = header.strip().lstrip("*").strip()
    return re.sub(r"(?<=[A-Za-z)])\d+$", "", name).strip()


def _cell_value(cell: str) -> str | None:
    text = cell.strip()
    if not text or text in _PLACEHOLDERS:
        return None
    percent = _percent_value(text)
    if percent is not None:
        return percent
    return _dollar_value(text)


def _percent_value(text: str) -> str | None:
    matches = list(_PERCENT.finditer(text))
    if not matches:
        return None
    prefix = text[: matches[0].start()]
    suffix = text[matches[-1].end() :]
    if re.search(r"[A-Za-z0-9$]", prefix):
        return None
    if not re.fullmatch(r"\s*(?:APR|APY)?[\d*†‡]*\s*", suffix, flags=re.I):
        return None
    return text[matches[0].start() : matches[-1].end()]


def _dollar_value(text: str) -> str | None:
    matches = list(_DOLLAR.finditer(text))
    if len(matches) != 1:
        return None
    match = matches[0]
    if match.start() != 0 or match.end() != len(text):
        return None
    return match.group(0)
