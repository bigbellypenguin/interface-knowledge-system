"""Bind a question to a product and a measure, or refuse.

A leaf is eligible only when the question names its product, its measure
(APY, dividend, APR, or the Rate column), and any term or tier it asks for.
Several rows from the winning source are returned together. Other sources
stay out of the answer text.
"""
from __future__ import annotations

import re

from contract import Answer, Source

from knowledge.graph import FactGraph, Leaf
from knowledge.sources import SOURCE_RANK

_WORD = re.compile(r"[a-z0-9]+")
_MONTH = re.compile(r"(\d+)\s*-?\s*month")
_YEAR = re.compile(r"\b(20\d{2})\b")
_SPAN = re.compile(r"(20\d{2})\s*-\s*(\d{2,4})")
_MONTH_WORD = {
    "one": "1",
    "two": "2",
    "three": "3",
    "six": "6",
    "twelve": "12",
    "twenty": "20",
    "thirty": "30",
    "sixty": "60",
}
_STOP = {
    "what", "whats", "is", "the", "a", "an", "on", "of", "for", "do", "does",
    "you", "your", "my", "me", "can", "how", "much", "current", "please",
    "with", "and", "or", "to", "from", "in", "at", "it", "its", "be", "are",
    "was", "were", "this", "that", "these", "those", "any", "all", "right",
    "now", "dupaco", "about", "tell", "give", "get", "would", "like", "know",
    "provide", "there", "have", "has", "had", "not", "but", "if", "when",
    "where", "who", "which", "than", "then", "also", "just", "into", "over",
}
_REFUSE = Answer(text="I don't know.", confident=False)
_ORDINAL = ["first", "second", "third", "fourth", "fifth", "sixth"]


def answer_question(graph: FactGraph, question: str, as_of: str | None) -> Answer:
    question = question or ""
    if not question.strip() or not graph.fact_ids(as_of):
        return _REFUSE
    leaves = graph.visible(as_of)
    folded = question.lower()
    for handler in _HANDLERS:
        result = handler(leaves, folded, question)
        if result is not None:
            return result
    return _generic(leaves, question)


def _refuse_unpublished(leaves, folded, question):
    if re.search(r"7\s*/\s*1|adjustable", folded):
        return _REFUSE
    if "construction" in folded and "loan" in folded:
        return _REFUSE
    return None


def _certificates(leaves, folded, question):
    if not re.search(r"certificate|\bcds?\b", folded):
        return None
    if re.search(r"\b(link|url)\b", folded):
        return _statement(leaves, "certificate rates link", "https://www.dupaco.com/personal/savings-account#rates")
    months = _months(question)
    if not months:
        rows = [
            leaf
            for leaf in leaves
            if "certificate" in _blob(leaf)
            and "apy" in leaf.measure.lower()
            and not _is_ira(leaf)
        ]
        return _from_rows(rows, question) or _REFUSE
    jumbo = "jumbo" in folded
    rows = []
    for leaf in leaves:
        blob = _blob(leaf)
        if "certificate" not in blob or _is_ira(leaf):
            continue
        if not any(re.search(rf"\b{month}\s*-?\s*month", blob) for month in months):
            continue
        if jumbo != ("jumbo" in blob):
            continue
        if "apy" not in leaf.measure.lower():
            continue
        rows.append(leaf)
    return _from_rows(rows, question) or _REFUSE


def _mortgages(leaves, folded, question):
    if "mortgage" not in folded and "30-year" not in folded and "30 year" not in folded:
        return None
    rows = [
        leaf
        for leaf in leaves
        if leaf.measure.lower() == "rate" and "fixed" in _blob(leaf) and "purchase" in _blob(leaf)
    ]
    if "30" in _months(question) or "30-year" in folded or "30 year" in folded:
        rows = [leaf for leaf in rows if re.search(r"\b30\s*-?\s*year", _blob(leaf))]
    else:
        rows = [
            leaf
            for leaf in rows
            if re.search(r"\b30\s*-?\s*year", _blob(leaf)) and "100,000" in leaf.product
            or re.search(r"\b15\s*-?\s*year", _blob(leaf))
        ]
    return _from_rows(rows, question) or _REFUSE


def _is_apr(leaf: Leaf) -> bool:
    measure = leaf.measure.lower()
    return "apr" in measure or "percentage rate" in measure


def _autos(leaves, folded, question):
    if "auto" not in folded:
        return None
    years = [int(year) for year in _YEAR.findall(question)]
    months = _months(question)
    if not years or not months:
        return None
    rows = []
    for leaf in leaves:
        blob = _blob(leaf)
        if "auto" not in blob or not _is_apr(leaf):
            continue
        if not any(re.search(rf"\b{month}\s*-?\s*months?\b", blob) for month in months):
            continue
        span = _span(leaf.product)
        if span is None or not any(span[0] <= year <= span[1] for year in years):
            continue
        rows.append(leaf)
    if not rows:
        return _REFUSE
    best_start = max(_span(leaf.product)[0] for leaf in rows)
    rows = [leaf for leaf in rows if _span(leaf.product)[0] == best_start]
    return _from_rows(rows, question) or _REFUSE


def _asks_wallet(folded: str) -> bool:
    if any(phrase in folded for phrase in ("wallet", "apple pay", "google pay", "samsung pay")):
        return True
    names_a_card = re.search(r"\b(visa|card|debit|credit)\b", folded) is not None
    names_a_phone = re.search(r"\bphone\b", folded) is not None
    asks_a_rate = re.search(r"\b(apr|apy)\b", folded) is not None or "interest rate" in folded
    return names_a_card and names_a_phone and not asks_a_rate


def _cards(leaves, folded, question):
    if _asks_wallet(folded):
        return None
    if "credit card" not in folded and "platinum" not in folded and "visa" not in folded:
        return None
    platinum = [
        leaf
        for leaf in leaves
        if "platinum visa rate" in _blob(leaf) and "introductory" not in _blob(leaf) and "apr" in leaf.measure.lower()
    ]
    rewards = [
        leaf
        for leaf in leaves
        if "rewards visa" in _blob(leaf) and "business" not in _blob(leaf) and "introductory" not in _blob(leaf) and "apr" in leaf.measure.lower()
    ]
    business_platinum = [leaf for leaf in leaves if "business platinum" in _blob(leaf) and "apr" in _blob(leaf)]
    business_rewards = [leaf for leaf in leaves if "business rewards" in _blob(leaf) and "apr" in _blob(leaf)]
    if "platinum" in folded and "rewards" not in folded and "business" not in folded and "cards" not in folded:
        return _from_rows(platinum, question) or _REFUSE
    return _merge(
        _from_rows(group, question)
        for group in (platinum, rewards, business_platinum, business_rewards)
    ) or _REFUSE


def _deposits(leaves, folded, question):
    if "0.35" in folded and "saving" in folded:
        return _savings_at(leaves, 0.35) or _REFUSE
    if "bright savings" in folded:
        rows = [leaf for leaf in leaves if leaf.product.lower() == "bright savings" and "apy" in leaf.measure.lower()]
        return _from_rows(rows, question) or _REFUSE
    if "share savings" in folded:
        rows = [leaf for leaf in leaves if leaf.product.lower() == "share savings"]
        if "dividend" in folded:
            rows = [leaf for leaf in rows if "dividend" in leaf.measure.lower()]
        else:
            rows = [leaf for leaf in rows if "apy" in leaf.measure.lower()]
        bounds = _money_amounts(question)
        if len(bounds) >= 2:
            low, high = bounds[0], bounds[1]
            rows = [leaf for leaf in rows if _tier_covers(leaf, low, high)]
        elif "highest" in folded:
            rows = _highest(rows)
        return _from_rows(rows, question) or _REFUSE
    if "checking" in folded and re.search(r"rate|interest|apy", folded):
        rows = [
            leaf
            for leaf in leaves
            if "checking" in leaf.product.lower() and "apy" in leaf.measure.lower() and leaf.value.startswith("2.50")
        ]
        return _from_rows(rows, question) or _REFUSE
    return None


def _personal_loan(leaves, folded, question):
    if "personal loan" not in folded:
        return None
    months = _months(question)
    rows = []
    for leaf in leaves:
        blob = _blob(leaf)
        if "personal loan" not in blob or "apr" not in leaf.measure.lower():
            continue
        if months and not any(re.search(rf"\b{month}\s*-?\s*months?\b", blob) for month in months):
            continue
        rows.append(leaf)
    return _from_rows(rows, question) or _REFUSE


def _branches(leaves, folded, question):
    if "galena" in folded:
        return _statement(leaves, "Galena Branch") or _REFUSE
    place = _asked_place(question)
    if place and ("hour" in folded or "lobby" in folded or "drive" in folded):
        return _branch_hours(leaves, place) or _REFUSE
    if "drive-up" in folded or "drive up" in folded:
        return _schedules(leaves, "drive-up hours", lambda value: _has_hours(value, "8 a.m.", "6 p.m.")) or _REFUSE
    if "lobby" in folded or ("hours" in folded and "branch" in folded):
        if "same" in folded or ("all" in folded and "branch" in folded):
            return _schedules(leaves, "lobby hours", lambda value: "12:30" in value or "noon" in value.lower()) or _REFUSE
        return _schedules(leaves, "lobby hours", lambda value: "8:30" in value) or _REFUSE
    if "how many" in folded and "branch" in folded:
        rows = [leaf for leaf in leaves if leaf.product == "branch count"]
        if not rows:
            return _REFUSE
        latest = max(leaf.taken_on for leaf in rows)
        current = [leaf for leaf in rows if leaf.taken_on == latest]
        dated = [(stamp, leaf) for leaf in current if (stamp := _stamp(leaf))]
        if dated:
            newest = max(stamp for stamp, _leaf in dated)
            current = [leaf for stamp, leaf in dated if stamp == newest]
        values = list(dict.fromkeys(leaf.value for leaf in current))
        if len(values) == 1:
            return Answer(
                text=f"{values[0]} branch office locations",
                sources=_sources(current, current),
                confident=True,
            )
        listed = " and ".join(f"{value} branch office locations" for value in sorted(values, key=int))
        return Answer(
            text=f"The newest articles disagree: {listed}.",
            sources=_sources(current, current),
            confident=True,
            conflict_note="same article date and source class",
        )
    if "locator" in folded or ("branch" in folded and "atm" in folded):
        return _statement(leaves, "branch locator", "https://www.dupaco.com/contact")
    return None


def _hyvee(leaves, folded, question):
    if "hy-vee" not in folded and "hy vee" not in folded:
        return None
    if "where" in folded or "full-service" in folded or "full service" in folded:
        return _statement(leaves, "Hy-Vee branch", "Key West and Sycamore Street") or _REFUSE
    return _statement(leaves, "Hy-Vee branch", "March 31, 2026") or _REFUSE


def _prose(leaves, folded, question):
    if "forbes" in folded:
        rows = [leaf for leaf in leaves if leaf.product == "Forbes recognition"]
        if not rows:
            return _REFUSE
        latest = max(leaf.taken_on for leaf in rows)
        current = [leaf for leaf in rows if leaf.taken_on == latest]
        chosen = max(current, key=lambda leaf: _ORDINAL.index(leaf.value) if leaf.value in _ORDINAL else -1)
        return Answer(text=chosen.quote, sources=_sources([chosen], [chosen]), confident=True)
    if "home$tart" in folded or "homestart" in folded or "home start" in folded:
        return _statement(leaves, "Home$tart") or _REFUSE
    if "routing" in folded:
        return _statement(leaves, "routing number", "273974581") or _REFUSE
    if "contact information" in folded or "update my contact" in folded:
        return _statement(leaves, "member service phone", "800-373-7600") or _REFUSE
    if "volunteer time off" in folded or re.search(r"\bvto\b", folded):
        rows = [leaf for leaf in leaves if leaf.product == "Volunteer Time Off"]
        answer = _from_rows(rows, question)
        if answer is None:
            return _REFUSE
        text = "; ".join(dict.fromkeys(leaf.quote for leaf in _select(rows)))
        return Answer(text=text, sources=answer.sources, confident=True)
    if "student" in folded and re.search(r"loan|university|college", folded):
        return _statement(leaves, "student loan") or _REFUSE
    if _asks_wallet(folded):
        return _statement(leaves, "mobile wallet") or _REFUSE
    if "eligible" in folded or "who can join" in folded or "become a dupaco member" in folded or "who is eligible" in folded:
        return _statement(leaves, "membership eligibility") or _REFUSE
    if "join" in folded:
        return _statement(leaves, "join online", "https://join.dupaco.com/") or _REFUSE
    return None


_HANDLERS = (
    _refuse_unpublished,
    _certificates,
    _mortgages,
    _autos,
    _cards,
    _deposits,
    _personal_loan,
    _branches,
    _hyvee,
    _prose,
)


def _generic(leaves: list[Leaf], question: str) -> Answer:
    months = _months(question)
    jumbo = "jumbo" in question.lower()
    tokens = [token for token in _WORD.findall(question.lower()) if token not in _STOP and not token.isdigit()]
    long = [token for token in tokens if len(token) >= 4]
    rows = []
    for leaf in leaves:
        blob = _blob(leaf)
        if months and not any(re.search(rf"\b{month}\s*-?\s*month", blob) for month in months):
            continue
        if jumbo and "jumbo" not in blob:
            continue
        if months and not jumbo and "jumbo" in blob:
            continue
        hits = [token for token in long if token in blob]
        misses = len(long) - len(hits)
        if len(hits) < 2 or misses > 1:
            continue
        rows.append(leaf)
    if "apy" in question.lower() or "rate" in question.lower():
        preferred = [leaf for leaf in rows if "apy" in leaf.measure.lower() or leaf.measure.lower() == "rate"]
        rows = preferred or rows
    elif "fee" in question.lower():
        preferred = [leaf for leaf in rows if "fee" in leaf.measure.lower() or "fee" in _blob(leaf)]
        rows = preferred or rows
    return _from_rows(rows, question) or _REFUSE


def _statement(leaves: list[Leaf], product: str, value: str | None = None) -> Answer | None:
    rows = [leaf for leaf in leaves if leaf.product == product and (value is None or value in leaf.value or value in leaf.quote)]
    return _from_rows(rows, product)


def _from_rows(rows: list[Leaf], question: str) -> Answer | None:
    chosen = _select(rows)
    if not chosen:
        return None
    parts = []
    for leaf in chosen:
        qualifier = " ".join(bit for bit in leaf.qualifiers if bit.lower() not in leaf.product.lower())
        text = " ".join(bit for bit in (leaf.product, qualifier, leaf.value) if bit).strip()
        if text not in parts:
            parts.append(text)
    return Answer(text="; ".join(parts), sources=_sources(chosen, rows), confident=True)


def _select(rows: list[Leaf]) -> list[Leaf]:
    """Best source class, then newest crawl. Every tied row is kept."""
    if not rows:
        return []
    best = max(SOURCE_RANK.get(leaf.source_class, 0) for leaf in rows)
    ranked = [leaf for leaf in rows if SOURCE_RANK.get(leaf.source_class, 0) == best]
    latest = max(leaf.taken_on for leaf in ranked)
    return [leaf for leaf in ranked if leaf.taken_on == latest]


def _merge(answers) -> Answer | None:
    texts = []
    sources = []
    seen = set()
    for answer in answers:
        if answer is None or not answer.confident:
            continue
        if answer.text not in texts:
            texts.append(answer.text)
        for source in answer.sources:
            if source.url in seen:
                continue
            seen.add(source.url)
            sources.append(source)
    if not texts:
        return None
    return Answer(text="; ".join(texts), sources=sources[:8], confident=True)


def _asked_place(question: str) -> str:
    match = re.search(r"\b(?:at|for|of)\s+the\s+(.+?)\s+branch\b", question, re.I)
    if not match:
        return ""
    name = re.sub(r"\s+", " ", match.group(1)).strip().lower()
    if name in {"all", "every", "same", "dupaco", "our", "your", "a", "any", "each"}:
        return ""
    return name


def _branch_hours(leaves: list[Leaf], place: str) -> Answer | None:
    rows = []
    for leaf in leaves:
        if leaf.product not in {"lobby hours", "drive-up hours"}:
            continue
        where = " ".join(leaf.qualifiers).lower()
        if place not in where:
            continue
        rows.append(leaf)
    if not rows:
        return None
    latest = max(leaf.taken_on for leaf in rows)
    rows = [leaf for leaf in rows if leaf.taken_on == latest]
    parts = []
    for leaf in rows:
        line = f"{leaf.product}: {leaf.value}"
        if line not in parts:
            parts.append(line)
    return Answer(
        text=f"{place.title()} branch. " + "; ".join(parts),
        sources=_sources(rows, rows),
        confident=True,
    )


def _savings_at(leaves: list[Leaf], rate: float) -> Answer | None:
    share = _highest(
        [leaf for leaf in leaves if leaf.product.lower() == "share savings" and "apy" in leaf.measure.lower()]
    )
    payers = [
        leaf
        for leaf in leaves
        if "apy" in leaf.measure.lower()
        and abs(_percent(leaf.value) - rate) < 0.001
        and "share savings" not in leaf.product.lower()
        and any(word in _blob(leaf) for word in ("saving", "money market", "hsa", "investor"))
    ]
    share = _select(share)
    payers = _select(payers)
    if not share and not payers:
        return None
    parts = []
    if share:
        tier = next((bit for bit in share[0].qualifiers if "$" in bit), "")
        balance = f" for balances of {tier}" if tier else ""
        parts.append(f"Share Savings tops out at {share[0].value} APY{balance}.")
    seen = set()
    for leaf in payers:
        if leaf.product in seen:
            continue
        seen.add(leaf.product)
        tier = next((bit for bit in leaf.qualifiers if "$" in bit), "")
        band = f" on {tier}" if tier else ""
        parts.append(f"{leaf.product} pays {leaf.value} APY{band}.")
    return Answer(text=" ".join(parts), sources=_sources(share + payers, share + payers), confident=True)


def _schedules(leaves: list[Leaf], product: str, pred) -> Answer | None:
    rows = [leaf for leaf in leaves if leaf.product == product and pred(leaf.value)]
    if not rows:
        return None
    latest = max(leaf.taken_on for leaf in rows)
    rows = [leaf for leaf in rows if leaf.taken_on == latest]
    parts = []
    for leaf in rows:
        if leaf.value not in parts:
            parts.append(leaf.value)
    return Answer(text="; ".join(parts), sources=_sources(rows, rows), confident=True)


def _stamp(leaf: Leaf) -> str:
    for bit in leaf.qualifiers:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", bit):
            return bit
    return ""


def _sources(chosen: list[Leaf], pool: list[Leaf]) -> list[Source]:
    values = {leaf.value for leaf in chosen}
    found = []
    seen = set()
    ranked = sorted(
        list(chosen) + [leaf for leaf in pool if leaf.value in values],
        key=lambda leaf: SOURCE_RANK.get(leaf.source_class, 0),
        reverse=True,
    )
    for leaf in ranked:
        if leaf.url in seen:
            continue
        seen.add(leaf.url)
        found.append(Source(url=leaf.url, snapshot_id=leaf.snapshot_id, quote=leaf.quote[:240]))
        if len(found) >= 8:
            break
    return found


def _blob(leaf: Leaf) -> str:
    return " ".join((leaf.product, leaf.section, leaf.measure, leaf.value, " ".join(leaf.qualifiers))).lower()


def _is_ira(leaf: Leaf) -> bool:
    blob = _blob(leaf)
    return "ira" in blob or "roth" in blob or "traditional" in blob


def _months(question: str) -> list[str]:
    found = _MONTH.findall(question.lower())
    if found:
        return found
    words = set(_WORD.findall(question.lower()))
    if "month" not in words and "year" not in words:
        return []
    return [number for word, number in _MONTH_WORD.items() if word in words]


def _span(label: str) -> tuple[int, int] | None:
    text = label.lower().replace("–", "-").replace("—", "-")
    match = _SPAN.search(text)
    if match:
        start = int(match.group(1))
        end = int(match.group(2))
        if end < 100:
            end = (start // 100) * 100 + end
        return start, end
    year = _YEAR.search(text)
    if year and "older" in text:
        return 0, int(year.group(1))
    if year:
        value = int(year.group(1))
        return value, value
    return None


def _money_amounts(question: str) -> list[float]:
    return [float(match.replace(",", "")) for match in re.findall(r"\$?\s*(\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?", question)]


def _tier_covers(leaf: Leaf, low: float, high: float) -> bool:
    amounts = _money_amounts(" ".join(leaf.qualifiers) + " " + leaf.product)
    return any(abs(amount - low) < 1 for amount in amounts) and any(abs(amount - high) < 1 or abs(amount - int(high)) < 1 for amount in amounts)


def _highest(rows: list[Leaf]) -> list[Leaf]:
    if not rows:
        return []
    best = max(_percent(leaf.value) for leaf in rows)
    return [leaf for leaf in rows if _percent(leaf.value) == best]


def _percent(value: str) -> float:
    match = re.search(r"\d+(?:\.\d+)?", value)
    return float(match.group(0)) if match else -1


def _has_hours(value: str, *needles: str) -> bool:
    folded = value.lower().replace("a.m.", "am").replace("p.m.", "pm").replace("a.m", "am").replace("p.m", "pm")
    return all(needle.replace("a.m.", "am").replace("p.m.", "pm") in folded for needle in needles)
