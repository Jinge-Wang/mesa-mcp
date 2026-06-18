"""Search MESA documentation: ranked local BM25, with a network searchindex.js fallback.

Local docs are preferred (no network, version-correct). The fallback parses the Sphinx
``searchindex.js`` (the same data the website's client-side search uses) and matches
against page titles — a best-effort substitute when no local docs are present.
"""
from __future__ import annotations

import json
import re

from .. import version
from . import fetch, index, sources

_WORD_RE = re.compile(r"[a-z0-9_]+")


def _network_search(env: dict, query: str, limit: int) -> list:
    """Parse the site's searchindex.js and rank pages by query-term title overlap."""
    base = sources.network_base(env)
    raw = fetch.http_get(base + "searchindex.js")  # raises RuntimeError if httpx missing
    match = re.search(r"setIndex\((.*)\)\s*;?\s*$", raw.strip(), re.DOTALL)
    data = json.loads(match.group(1) if match else raw)

    docnames = data.get("docnames", [])
    q_terms = _WORD_RE.findall(query.lower())
    if not q_terms:
        return []

    results = []

    def add(title: str, docid, anchor=None):
        if not isinstance(docid, int) or docid < 0 or docid >= len(docnames):
            return
        hits = sum(1 for t in q_terms if t in title.lower())
        if not hits:
            return
        url = base + docnames[docid] + ".html" + (f"#{anchor}" if anchor else "")
        results.append({"score": hits, "title": title, "url": url})

    alltitles = data.get("alltitles")
    if isinstance(alltitles, dict):
        for title, refs in alltitles.items():
            for ref in refs:
                if isinstance(ref, list) and ref:
                    add(title, ref[0], ref[1] if len(ref) > 1 else None)
                else:
                    add(title, ref)
    else:  # older Sphinx: a `titles` list parallel to docnames
        for i, title in enumerate(data.get("titles", [])):
            add(title, i)

    # Deduplicate by URL, keep highest score, then rank.
    best: dict = {}
    for r in results:
        if r["url"] not in best or r["score"] > best[r["url"]]["score"]:
            best[r["url"]] = r
    ranked = sorted(best.values(), key=lambda r: r["score"], reverse=True)
    return ranked[:limit]


def search_docs(env: dict, query: str, limit: int = 10) -> dict:
    """Search docs; returns {source, docs_version, results, [note]}.

    Uses the local BM25 index when local docs exist; otherwise the network fallback.
    """
    idx = index.get_local_index(env)
    if idx is not None:
        return {
            "source": "local",
            "docs_version": version.docs_version(env),
            "results": idx.search(query, limit),
        }

    base = {"docs_version": version.docs_version(env), "results": []}
    try:
        return {"source": "network", **base, "results": _network_search(env, query, limit)}
    except RuntimeError as e:  # deps missing
        return {"source": "unavailable", **base, "note": str(e)}
    except Exception as e:  # network/parse failure
        return {"source": "network-error", **base, "note": f"Network search failed: {e}"}
