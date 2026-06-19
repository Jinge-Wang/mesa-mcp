"""FastMCP tools — documentation & reference knowledge (``mesa_docs_*``), local-first.

Docs search/fetch, the authoritative option reference, test-suite discovery, and an optional
local docs web server.
"""
from __future__ import annotations

import json
import os

from .. import docs_server, reference
from ..docs import fetch, sources, test_suite
from ..docs import search as search_mod
from ..environment import build_env_context


def _format_search(res: dict, query: str) -> str:
    header = (f"docs search: '{query}'  "
              f"[source={res['source']}, docs_version={res.get('docs_version', '?')}]")
    results = res.get("results", [])
    if not results:
        note = res.get("note", "")
        return header + "\nNo matches." + (f"\nNote: {note}" if note else "")
    lines = [header, ""]
    for i, r in enumerate(results, 1):
        if "url" in r:  # network result
            lines.append(f"{i}. {r['title']}  (score {r['score']})")
            lines.append(f"   {r['url']}")
        else:  # local result
            head = f" › {r['heading']}" if r.get("heading") and r["heading"] != r["title"] else ""
            lines.append(f"{i}. {r['title']}{head}  (score {r['score']})")
            lines.append(f"   {r['source']}")
            if r.get("snippet"):
                lines.append(f"   {r['snippet']}")
    return "\n".join(lines)


def _format_index(res: dict) -> str:
    if res.get("source") in ("unavailable", "network-error"):
        return f"Test-suite index unavailable: {res.get('note', '')}"
    lines = [f"MESA test suite [source={res['source']}, docs_version={res.get('docs_version', '?')}]"]
    if res.get("modules"):
        for module, cases in res["modules"].items():
            lines.append(f"\n{module} ({len(cases)}):")
            lines.append("  " + ", ".join(cases))
    elif res.get("cases"):
        lines.append(f"\ncases ({len(res['cases'])}):")
        lines.append("  " + ", ".join(res["cases"]))
    return "\n".join(lines)


def _format_details(res: dict) -> str:
    if res.get("source") in ("unavailable", "network-error"):
        return f"Details for '{res.get('test_name', '?')}' unavailable: {res.get('note', '')}"
    title = f"# {res['test_name']}  [source={res['source']}"
    if res.get("module"):
        title += f", module={res['module']}"
    title += "]"
    lines = [title]
    if res.get("case_dir"):
        lines.append(f"case_dir: {res['case_dir']}")
    if res.get("url"):
        lines.append(f"url: {res['url']}")
    lines.append("\n## Description\n" + (res.get("description") or "(none)"))
    if res.get("inlist_files"):
        lines.append("\n## Inlist files\n" + ", ".join(res["inlist_files"]))
    for name, content in (res.get("inlists") or {}).items():
        lines.append(f"\n## {name}\n```fortran\n{content}\n```")
    if res.get("auxiliary_files"):
        lines.append("\n## Other files present\n" + ", ".join(res["auxiliary_files"]))
    if res.get("note"):
        lines.append("\nNote: " + res["note"])
    return "\n".join(lines)


def _resolve_local(local_dir: str, rel: str) -> "str | None":
    """Resolve a doc path under local_dir (guarding traversal); try a .rst suffix."""
    base = os.path.realpath(local_dir)
    cand = os.path.realpath(os.path.join(base, rel.strip().lstrip("/")))
    if cand != base and not cand.startswith(base + os.sep):
        return None
    for p in (cand, cand + ".rst"):
        if os.path.isfile(p):
            return p
    return None


def _format_option(res: dict, name: str) -> str:
    exact = res.get("exact", [])
    related = res.get("related", [])
    if not exact and not related:
        return (f"No MESA option found matching '{name}'. Check the spelling, or use "
                "mesa_docs_search for a broader search. (Requires MESA_DIR with defaults files.)")
    lines = []
    for o in exact:
        default = o["default"] if o["default"] is not None else "(no simple default)"
        lines.append(f"# {o['name']}   [&{o['namelist']}, {o['module']} module]")
        lines.append(f"default: {o['name']} = {default}")
        lines.append("")
        lines.append(o["doc"] or "(no documentation)")
        lines.append("")
    if related:
        lines.append(f"No exact match for '{name}'. Related options:")
        for o in related:
            d = f"  default: {o['default']}" if o["default"] is not None else ""
            lines.append(f"  - {o['name']}  [&{o['namelist']}]{d}")
    return "\n".join(lines).strip()


def register(mcp) -> None:
    @mcp.tool()
    def mesa_docs_option(name: str, namelist: str = "") -> str:
        """Look up a MESA inlist control/option by name and return its namelist, default
        value, and full documentation — parsed from the authoritative *.defaults files in
        $MESA_DIR (controls, star_job, eos, kap, pgstar, and the binary namelists
        binary_controls / binary_job / pgbinary, plus astero). This is the precise way to VERIFY a
        control and its default before writing it into an inlist; prefer it over guessing. If there
        is no exact match, returns related option names.

        Args:
            name: the control name (e.g. 'initial_mass', 'use_Type2_opacities', 'mass_transfer_alpha').
            namelist: optional namelist filter (e.g. 'controls', 'star_job', 'binary_controls').
        """
        env = build_env_context()
        return _format_option(reference.lookup(env, name, namelist or None), name)

    @mcp.tool()
    def mesa_docs_search(query: str, limit: int = 10) -> str:
        """Search the MESA documentation and return the top ranked matches (title,
        section, source path/URL, and a snippet). Reads the local docs in
        $MESA_DIR/docs/source first (offline, version-correct); falls back to
        docs.mesastar.org only when no local docs exist. Use this to verify control and
        namelist names and parameter formatting before writing inlists — do not rely on
        memory.

        Args:
            query: free-text query (natural language or a MESA control name).
            limit: maximum number of results (1–50, default 10).
        """
        env = build_env_context()
        limit = max(1, min(int(limit), 50))
        return _format_search(search_mod.search_docs(env, query, limit), query)

    @mcp.tool()
    def mesa_docs_page(path_or_url: str) -> str:
        """Fetch the full text of one MESA documentation page. Accepts a local docs path
        (e.g. 'reference/star_job', 'reference/binary_job', 'test_suite', with or without .rst)
        resolved under $MESA_DIR/docs/source, or an absolute http(s) URL. Returns readable plain
        text. Pair with mesa_docs_search to read a promising result in full."""
        env = build_env_context()
        target = path_or_url.strip()

        if target.startswith(("http://", "https://")):
            try:
                return fetch.html_to_text(fetch.http_get(target))
            except Exception as e:
                return f"Error fetching {target}: {e}"

        local_dir = sources.local_docs_dir(env)
        if local_dir:
            resolved = _resolve_local(local_dir, target)
            if resolved:
                try:
                    with open(resolved, "r", encoding="utf-8", errors="replace") as f:
                        return fetch.rst_to_text(f.read())
                except OSError as e:
                    return f"Error reading {resolved}: {e}"

        page = target[:-4] if target.endswith(".rst") else target
        url = sources.network_base(env) + page + ("" if page.endswith(".html") else ".html")
        try:
            return fetch.html_to_text(fetch.http_get(url))
        except Exception as e:
            return f"Could not resolve '{path_or_url}' locally or via network ({url}): {e}"

    @mcp.tool()
    def mesa_docs_testsuite(case: str = "") -> str:
        """Browse the MESA test suite (verified example setups). With no `case`, lists all cases
        grouped by module (star/binary/astero). With a `case` name, returns that case's description
        and its real inlist configurations — the verified baseline to copy into a new work folder
        (via mesa_work_create). Local-first from $MESA_DIR; network fallback for the index +
        descriptions (real inlists exist only in a local install).

        Args:
            case: a case name (e.g. '1M_pre_ms_to_wd'); empty lists the whole index.
        """
        env = build_env_context()
        case = case.strip()
        if not case:
            return _format_index(test_suite.index(env))
        return _format_details(test_suite.details(env, case))

    @mcp.tool()
    def mesa_docs_serve(action: str = "start", port: int = 8000, rebuild: bool = False) -> str:
        """Serve the installed MESA documentation as a local website (detached), or stop it.

        - `action="start"` (default): serve the docs and return the URL. The install ships only
          Sphinx `.rst` source, so by default this serves an existing built HTML tree if present,
          else the raw source. Pass `rebuild=True` to build browsable HTML with `sphinx-build` first
          (best-effort; needs the docs' Sphinx requirements and can take a few minutes).
        - `action="stop"`: stop the running docs server.

        For quick lookups prefer mesa_docs_search / mesa_docs_page (no server needed).

        Args:
            action: "start" or "stop".
            port: (start) preferred local port (an open port is chosen if it's taken).
            rebuild: (start) build HTML with sphinx-build before serving.
        """
        act = action.strip().lower()
        if act == "stop":
            return json.dumps(docs_server.stop_docs(), indent=2)
        if act == "start":
            return json.dumps(docs_server.serve_docs(build_env_context(), port, rebuild), indent=2)
        return json.dumps({"error": f"Unknown action '{action}'. Use 'start' or 'stop'."}, indent=2)
