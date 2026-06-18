"""Search publications that used MESA via the Zenodo 'mesa' community REST API.

The Zenodo records web page is JS-rendered, so we use the REST API directly:
``/api/records?communities=mesa&q=<query>`` → JSON hits with title, creators, DOI, date.
"""
from __future__ import annotations

import json
from urllib.parse import quote

from ..docs import fetch

ZENODO_RECORDS_API = "https://zenodo.org/api/records"


def search(query: str, limit: int = 10) -> dict:
    """Return MESA-community publications matching ``query`` (title, authors, DOI, date, url)."""
    url = (f"{ZENODO_RECORDS_API}?communities=mesa&q={quote(query)}"
           f"&size={max(1, min(limit, 50))}&sort=bestmatch")
    data = json.loads(fetch.http_get(url, cache=False))
    hits = (data.get("hits") or {}).get("hits", [])

    results = []
    for h in hits:
        meta = h.get("metadata") or {}
        results.append({
            "title": meta.get("title") or h.get("title"),
            "authors": [c.get("name", "") for c in meta.get("creators", [])],
            "doi": meta.get("doi"),
            "date": meta.get("publication_date"),
            "url": (h.get("links") or {}).get("self_html"),
        })
    return {"total": (data.get("hits") or {}).get("total"), "results": results}
