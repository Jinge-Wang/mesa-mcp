"""Community add-ons from the MESA marketplace: search the add-ons table.

The marketplace add-ons page (``mesastar.org/marketplace/add-ons/``) is a static 6-column HTML
table (Author, Type, Description, Language, MESA version, Get → link). These are user-contributed
tools, repositories, and extensions (run_star_extras helpers, plotting tools, utilities). We scrape
and rank it like the inlists table; the ``Get`` link points to the upstream repo/page.
"""
from __future__ import annotations

import re

from ..docs import fetch

ADDONS_URL = "https://mesastar.org/marketplace/add-ons/"

_WORD_RE = re.compile(r"[a-z0-9_]+")
_ENTRIES: "list | None" = None


def _parse_table(html: str) -> list:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for tr in soup.select("table tr"):
        tds = tr.find_all("td")
        if len(tds) < 6:
            continue
        links = [a.get("href", "") for a in tds[5].find_all("a")] or \
                [a.get("href", "") for a in tr.find_all("a")]
        entries.append({
            "author": tds[0].get_text(strip=True),
            "type": tds[1].get_text(strip=True),
            "description": tds[2].get_text(strip=True),
            "language": tds[3].get_text(strip=True),
            "mesa_version": tds[4].get_text(strip=True),
            "links": [l for l in links if l],
        })
    return entries


def fetch_entries(force: bool = False) -> list:
    """Return the parsed marketplace add-on entries (cached for the session)."""
    global _ENTRIES
    if _ENTRIES is None or force:
        _ENTRIES = _parse_table(fetch.http_get(ADDONS_URL))
    return _ENTRIES


def search(query: str, limit: int = 10) -> list:
    """Rank marketplace add-ons by query-term overlap in description/author/type/language."""
    entries = fetch_entries()
    terms = _WORD_RE.findall(query.lower())
    scored = []
    for i, e in enumerate(entries):
        hay = f"{e['description']} {e['author']} {e['type']} {e['language']}".lower()
        score = sum(hay.count(t) for t in terms) if terms else 1
        if score:
            scored.append((score, i, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{**e, "index": i, "score": score} for score, i, e in scored[:limit]]
