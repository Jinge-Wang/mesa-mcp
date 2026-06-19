"""FastMCP tools — ecosystem discovery (``mesa_find_*``): community inlists, publications,
the wider Zenodo community, and marketplace add-ons, plus session-download management.
"""
from __future__ import annotations

import json

from .. import config
from ..knowledge import addons, inlists, publications


def _format_inlists(results: list, query: str) -> str:
    if not results:
        return f"community inlists: '{query}'\nNo matches."
    lines = [f"community inlists: '{query}'  ({len(results)} shown)", ""]
    for r in results:
        lines.append(f"[{r['index']}] {r['title']}  — {r['author']}  (MESA {r['mesa_version']})")
        if r.get("paper_url"):
            lines.append(f"     paper: {r['paper_url']}")
        if r.get("download_url"):
            lines.append(f"     download: {r['download_url']}")
    lines.append("\nUse mesa_find_download(<index or title>) to fetch one (ephemeral).")
    return "\n".join(lines)


def _format_pubs(res: dict, query: str) -> str:
    results = res.get("results", [])
    header = f"MESA publications: '{query}'  (total ~{res.get('total', '?')}, {len(results)} shown)"
    if not results:
        return header + "\nNo matches."
    lines = [header, ""]
    for i, r in enumerate(results, 1):
        authors = ", ".join(r["authors"][:4]) + (" et al." if len(r["authors"]) > 4 else "")
        lines.append(f"{i}. {r['title']}  ({r.get('date', '?')})")
        if authors:
            lines.append(f"   {authors}")
        meta = "   " + "  ".join(filter(None, [
            f"doi:{r['doi']}" if r.get("doi") else "", r.get("url") or ""]))
        if meta.strip():
            lines.append(meta)
    return "\n".join(lines)


def _format_addons(results: list, query: str) -> str:
    if not results:
        return f"MESA add-ons: '{query}'\nNo matches."
    lines = [f"MESA add-ons: '{query}'  ({len(results)} shown)", ""]
    for r in results:
        lines.append(f"[{r['index']}] {r['description']}")
        lines.append(f"     {r['author']}  | {r['type']} | {r['language']} | MESA {r['mesa_version']}")
        for link in r["links"]:
            lines.append(f"     {link}")
    return "\n".join(lines)


def _format_download(res: dict) -> str:
    if res.get("error"):
        return f"Download failed: {res['error']}"
    lines = [f"Downloaded '{res['title']}' — {res.get('author', '')}  (Zenodo {res['zenodo_id']})"]
    if res.get("record_url"):
        lines.append(f"record: {res['record_url']}")
    lines.append(f"saved to (session scratch, purged on exit): {res['dest']}")
    for f in res.get("files", []):
        if f.get("error"):
            lines.append(f"  - {f['file']}: ERROR {f['error']}")
        else:
            lines.append(f"  - {f['file']}  ({f['bytes']} bytes)  {f['path']}")
    return "\n".join(lines)


def register(mcp) -> None:
    @mcp.tool()
    def mesa_find_search(query: str, source: str = "inlists", limit: int = 10,
                         resource_type: str = "") -> str:
        """Search the MESA ecosystem for shared resources. Pick a `source`:

        - `inlists` (default) — the marketplace of community-shared **inlists** (by title/author),
          with the linked paper + Zenodo download. Fetch one with mesa_find_download.
        - `publications` — papers that used MESA (Zenodo 'mesa' community): authors, DOI, date, link.
        - `zenodo` — the whole MESA Zenodo community across **all record types** (software, datasets,
          inlist bundles, publications) with each record's type/version/DOI and **downloadable
          files** (JSON). Optionally filter with `resource_type` (e.g. 'software', 'dataset').
        - `addons` — marketplace add-ons (run_star_extras helpers, plotting utilities, …).
        - `all` — a combined text summary of inlists + publications + addons.

        Args:
            query: free-text query (title, author, topic, object).
            source: 'inlists', 'publications', 'zenodo', 'addons', or 'all'.
            limit: maximum number of results (1–50, default 10).
            resource_type: (zenodo only) Zenodo type filter ('' = all).
        """
        src = source.strip().lower()
        limit = max(1, min(int(limit), 50))

        def _one(s: str) -> "str | None":
            if s == "inlists":
                return _format_inlists(inlists.search(query, limit), query)
            if s == "publications":
                return _format_pubs(publications.search(query, limit), query)
            if s == "zenodo":
                return json.dumps(publications.search_records(query, resource_type, limit), indent=2)
            if s == "addons":
                return _format_addons(addons.search(query, limit), query)
            return None

        if src == "all":
            parts = []
            for s in ("inlists", "publications", "addons"):
                try:
                    parts.append(f"=== {s} ===\n{_one(s)}")
                except Exception as e:
                    parts.append(f"=== {s} ===\n(could not reach this source: {e})")
            parts.append("(For software/datasets/paper-linked files, run source='zenodo'.)")
            return "\n\n".join(parts)

        try:
            out = _one(src)
        except Exception as e:
            return f"Could not reach the '{source}' source: {e}"
        if out is None:
            return (f"Unknown source '{source}'. Use 'inlists', 'publications', 'zenodo', "
                    "'addons', or 'all'.")
        return out

    @mcp.tool()
    def mesa_find_download(identifier: str) -> str:
        """Download a community inlist's files from Zenodo into an ephemeral session scratch
        directory (purged when the server exits, so it never bloats your disk). Returns the
        saved file paths.

        Args:
            identifier: an index from mesa_find_search(source='inlists'), or a title substring.
        """
        try:
            return _format_download(inlists.download(identifier))
        except Exception as e:
            return f"Download failed: {e}"

    @mcp.tool()
    def mesa_find_clear() -> str:
        """Purge the session scratch directory now (community-inlist downloads). It is also
        purged automatically when the server exits."""
        return ("Session downloads cleared." if config.cleanup_session()
                else "Nothing to clear — no session downloads exist.")
