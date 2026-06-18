"""FastMCP tools: output-column reference and context-efficient history slices."""
from __future__ import annotations

import re

from .. import columns as columns_mod
from ..environment import build_env_context


def _format_column(res: dict, name: str) -> str:
    exact = res.get("exact", [])
    related = res.get("related", [])
    kind = res.get("kind")
    if not exact and not related:
        return f"No {kind} column matching '{name}'. ({res.get('total', 0)} columns available.)"
    lines = []
    for c in exact:
        sel = "selected by default" if c["selected"] else "available (not selected by default)"
        lines.append(f"# {c['name']}  ({kind} column, {sel})")
        lines.append(c["doc"] or "(no documentation)")
        lines.append("")
    if related:
        lines.append(f"No exact match for '{name}'. Related {kind} columns:")
        for c in related:
            lines.append(f"  - {c['name']}" + (f"  — {c['doc']}" if c["doc"] else ""))
    return "\n".join(lines).strip()


def _format_history(res: dict) -> str:
    if res.get("error"):
        return f"Could not read history: {res['error']}"
    cols = res["columns"]
    if not cols:
        return f"history: {res['file']}\nNo matching columns to show."
    lines = [
        f"history: {res['file']}",
        f"models: {res['total_models']} total, showing {res['shown']}"
        + (f" (every {res['every']})" if res["every"] > 1 else ""),
    ]
    if res.get("missing"):
        lines.append(f"(unknown columns ignored: {', '.join(res['missing'])})")
    widths = [len(c) for c in cols]
    for row in res["rows"]:
        for i, v in enumerate(row):
            widths[i] = max(widths[i], len(v))
    lines.append("  ".join(c.ljust(widths[i]) for i, c in enumerate(cols)))
    for row in res["rows"]:
        lines.append("  ".join(v.ljust(widths[i]) for i, v in enumerate(row)))
    return "\n".join(lines)


def register(mcp) -> None:
    @mcp.tool()
    def mesa_get_output_column(name: str, kind: str = "history") -> str:
        """Look up a MESA output column by name: whether it is selected by default and its
        documentation, from the master history/profile `*_columns.list` files in $MESA_DIR.
        Use to discover or verify output quantities before configuring `history_columns.list`
        / `profile_columns.list`.

        Args:
            name: the column name (e.g. 'log_L', 'center_h1', 'he_core_mass').
            kind: 'history' (default) or 'profile'.
        """
        return _format_column(columns_mod.lookup(build_env_context(), name, kind), name)

    @mcp.tool()
    def mesa_read_history(path: str, columns: str = "", last_n: int = 20, every: int = 1) -> str:
        """Read a context-efficient slice of a run's `LOGS/history.data`: only the selected
        columns, the last N models, optionally downsampled — never the whole table. Use this
        instead of cat-ing history.data.

        Args:
            path: a workspace directory, a LOGS directory, or a history.data file.
            columns: comma/space-separated column names (default: a key set if present).
            last_n: number of most-recent models to show (default 20).
            every: stride for downsampling rows (default 1 = every model).
        """
        cols = [c for c in re.split(r"[,\s]+", columns.strip()) if c] or None
        res = columns_mod.read_history(build_env_context(), path, cols, last_n, every)
        return _format_history(res)
