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


def search_records(query: str, resource_type: str = "", limit: int = 10) -> dict:
    """Search the MESA Zenodo community across record types, with download links.

    Unlike ``search`` (papers only), this surfaces software, datasets, and pre-built inlist
    bundles — e.g. "the inlist used for paper X" — including each record's type and downloadable
    files. ``resource_type`` optionally filters (e.g. ``software``, ``dataset``, ``publication``).
    """
    url = (f"{ZENODO_RECORDS_API}?communities=mesa&q={quote(query)}"
           f"&size={max(1, min(limit, 50))}&sort=bestmatch")
    if resource_type.strip():
        url += f"&type={quote(resource_type.strip())}"
    try:
        data = json.loads(fetch.http_get(url, cache=False))
    except Exception as e:
        return {"error": f"Zenodo query failed: {e}"}
    hits = (data.get("hits") or {}).get("hits", [])

    results = []
    for h in hits:
        meta = h.get("metadata") or {}
        files = []
        for f in (h.get("files") or [])[:10]:
            files.append({
                "name": f.get("key"),
                "size_mb": round(f.get("size", 0) / 1e6, 2) if f.get("size") else None,
                "download_url": (f.get("links") or {}).get("self"),
            })
        results.append({
            "title": meta.get("title") or h.get("title"),
            "type": (meta.get("resource_type") or {}).get("type"),
            "authors": [c.get("name", "") for c in meta.get("creators", [])][:6],
            "version": meta.get("version"),
            "doi": meta.get("doi"),
            "date": meta.get("publication_date"),
            "url": (h.get("links") or {}).get("self_html"),
            "n_files": len(h.get("files") or []),
            "files": files,
        })
    return {"total": (data.get("hits") or {}).get("total"), "results": results}
