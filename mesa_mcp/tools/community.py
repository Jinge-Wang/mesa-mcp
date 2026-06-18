"""FastMCP tools: community inlists and MESA publications (network knowledge)."""
from __future__ import annotations

from .. import config
from ..knowledge import inlists, publications


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
    lines.append("\nUse mesa_download_community_inlist(<index or title>) to fetch one (ephemeral).")
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


def register(mcp) -> None:
    @mcp.tool()
    def mesa_search_community_inlists(query: str, limit: int = 10) -> str:
        """Search the MESA marketplace of community-shared inlists by title/author. Returns
        ranked entries with the linked paper (adsabs) and Zenodo download. Use this to find
        a published setup to learn from, then mesa_download_community_inlist to fetch it.

        Args:
            query: free-text query matched against title and author.
            limit: maximum number of results (default 10).
        """
        try:
            return _format_inlists(inlists.search(query, limit), query)
        except Exception as e:
            return f"Could not reach the inlist marketplace: {e}"

    @mcp.tool()
    def mesa_download_community_inlist(identifier: str) -> str:
        """Download a community inlist's files from Zenodo into an ephemeral session scratch
        directory (purged when the server exits, so it never bloats your disk). Returns the
        saved file paths.

        Args:
            identifier: an index from mesa_search_community_inlists, or a title substring.
        """
        try:
            return _format_download(inlists.download(identifier))
        except Exception as e:
            return f"Download failed: {e}"

    @mcp.tool()
    def mesa_search_publications(query: str, limit: int = 10) -> str:
        """Search publications that used MESA via the Zenodo 'mesa' community. Returns ranked
        papers with authors, DOI, date, and record link — handy for pointing the user at prior
        work relevant to their model.

        Args:
            query: free-text query (topic, method, object type, …).
            limit: maximum number of results (1–50, default 10).
        """
        try:
            return _format_pubs(publications.search(query, limit), query)
        except Exception as e:
            return f"Could not reach the Zenodo MESA community: {e}"

    @mcp.tool()
    def mesa_clear_downloads() -> str:
        """Purge the session scratch directory now (community-inlist downloads). It is also
        purged automatically when the server exits."""
        return ("Session downloads cleared." if config.cleanup_session()
                else "Nothing to clear — no session downloads exist.")
