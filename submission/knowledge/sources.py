"""Where a page sits in the source hierarchy. Higher rank wins."""
from __future__ import annotations

import re
from urllib.parse import urlparse

SOURCE_RANK = {
    "rate_sheet": 400,
    "product": 300,
    "reference": 200,
    "news": 120,
    "promo": 40,
    "archive": 10,
}

_DATED = re.compile(r"/20\d{2}/")
_PROMO_PATH = ("switch-and-earn", "/calculators", "-lp", "/promo")


def classify_source(url: str, title: str = "", text: str = "") -> str:
    parsed = urlparse(url if "//" in (url or "") else "https://" + (url or ""))
    path = parsed.path.lower().rstrip("/")
    blob = f"{title}\n{(text or '')[:800]}".lower()

    if path.endswith("/promo") or "/promo/" in f"{path}/" or "offer ended" in blob:
        return "promo"
    if path == "/rates" or path.endswith("/rates") or "/rates/" in f"{path}/":
        return "rate_sheet"
    if "/newsroom" in path:
        return "news"
    if _DATED.search(path) or "/learn/blog" in path or "homebuying-guidance" in path:
        return "archive"
    if any(piece in path for piece in _PROMO_PATH):
        return "promo"
    if path.endswith("/contact") or "/about" in path:
        return "reference"
    if "/fees" in path or "/personal/" in path or "/business/" in path:
        return "product"
    return "archive"
