"""Community inlists from the MESA marketplace: search the table, download from Zenodo.

The marketplace page (``mesastar.org/marketplace/inlists/``) is a static 5-column HTML
table (Author, Title, Paper Link → adsabs, MESA version, Download → Zenodo DOI). Downloads
resolve the Zenodo DOI via the Zenodo REST API and stream the record's files into the
session scratch dir, which is purged on server exit.
"""
from __future__ import annotations

import json
import os
import re

from .. import config
from ..docs import fetch

MARKETPLACE_URL = "https://mesastar.org/marketplace/inlists/"
ZENODO_RECORD_API = "https://zenodo.org/api/records/"

_WORD_RE = re.compile(r"[a-z0-9_]+")
_ZENODO_ID_RE = re.compile(r"zenodo\.(\d+)", re.IGNORECASE)

# Per-session cache of the parsed table (avoid re-scraping on every search).
_ENTRIES: "list | None" = None


def _parse_table(html: str) -> list:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    entries = []
    for tr in soup.select("table tr"):
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue
        paper_a = tds[2].find("a")
        dl_a = tds[4].find("a")
        entries.append({
            "author": tds[0].get_text(strip=True),
            "title": tds[1].get_text(strip=True),
            "paper_url": paper_a.get("href", "") if paper_a else "",
            "mesa_version": tds[3].get_text(strip=True),
            "download_url": dl_a.get("href", "") if dl_a else "",
        })
    return entries


def fetch_entries(force: bool = False) -> list:
    """Return the parsed marketplace inlist entries (cached for the session)."""
    global _ENTRIES
    if _ENTRIES is None or force:
        _ENTRIES = _parse_table(fetch.http_get(MARKETPLACE_URL))
    return _ENTRIES


def search(query: str, limit: int = 10) -> list:
    """Rank marketplace inlists by query-term overlap in title + author."""
    entries = fetch_entries()
    terms = _WORD_RE.findall(query.lower())
    scored = []
    for i, e in enumerate(entries):
        hay = f"{e['title']} {e['author']}".lower()
        score = sum(hay.count(t) for t in terms) if terms else 1
        if score:
            scored.append((score, i, e))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [{**e, "index": i, "score": score} for score, i, e in scored[:limit]]


def _resolve(identifier: str, entries: list) -> "dict | None":
    """Resolve an entry by integer index (as string) or a title substring match."""
    ident = identifier.strip()
    if ident.isdigit():
        idx = int(ident)
        return entries[idx] if 0 <= idx < len(entries) else None
    low = ident.lower()
    return next((e for e in entries if low in e["title"].lower()), None)


def download(identifier: str, max_files: int = 20) -> dict:
    """Download a marketplace inlist's Zenodo files into the session scratch dir.

    `identifier` is an index from search() or a title substring. Returns the saved paths.
    """
    entries = fetch_entries()
    entry = _resolve(identifier, entries)
    if entry is None:
        return {"error": f"No inlist matched '{identifier}'. Use an index or title from search."}

    zid = _ZENODO_ID_RE.search(entry.get("download_url", ""))
    if not zid:
        return {"error": f"No Zenodo id in download link: {entry.get('download_url')!r}"}
    record_id = zid.group(1)

    try:
        data = json.loads(fetch.http_get(ZENODO_RECORD_API + record_id, cache=False))
    except Exception as e:
        return {"error": f"Zenodo lookup failed for record {record_id}: {e}"}

    dest_root = os.path.join(config.session_dir(), f"inlist_{record_id}")
    os.makedirs(dest_root, exist_ok=True)

    saved = []
    for f in data.get("files", [])[:max_files]:
        key = f.get("key") or "file"
        links = f.get("links") or {}
        link = links.get("content") or links.get("download") or links.get("self")
        if not link:
            continue
        dest = os.path.join(dest_root, os.path.basename(key))
        try:
            n = fetch.http_download(link, dest)
            saved.append({"file": key, "path": dest, "bytes": n})
        except Exception as e:
            saved.append({"file": key, "error": str(e)})

    return {
        "title": entry["title"],
        "author": entry["author"],
        "zenodo_id": record_id,
        "record_url": (data.get("links") or {}).get("self_html"),
        "dest": dest_root,
        "files": saved,
    }
