"""FastMCP tools — read & analyze MESA data (``mesa_data_*``): history slices, output-column
reference, run analyzers, the bundled data libraries, and nuclear reaction rates.
"""
from __future__ import annotations

import json
import re

from .. import analysis, columns as columns_mod, data_libs, rates
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
    def mesa_data_history(path: str, columns: str = "", last_n: int = 20, every: int = 1,
                          star: str = "") -> str:
        """Read a context-efficient slice of a run's history.data: only the selected
        columns, the last N models, optionally downsampled — never the whole table. The actual
        log directory / history filename are resolved from the inlist chain (so a renamed
        `log_directory`/`star_history_name` is honored). Use this instead of cat-ing history.data.

        For a **binary** run, set `star` to `"1"`/`"2"` for that component's history, or `"binary"`
        for `binary_history.data` (orbital quantities: period, separation, mass-transfer rate, RLOF).

        Args:
            path: a workspace directory, a LOGS directory, or a history.data file.
            columns: comma/space-separated column names (default: a key set if present).
            last_n: number of most-recent models to show (default 20).
            every: stride for downsampling rows (default 1 = every model).
            star: binary component selector — '1', '2', 'binary', or '' (single-star).
        """
        cols = [c for c in re.split(r"[,\s]+", columns.strip()) if c] or None
        res = columns_mod.read_history(build_env_context(), path, cols, last_n, every, star)
        return _format_history(res)

    @mcp.tool()
    def mesa_data_column(name: str, kind: str = "history") -> str:
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
    def mesa_data_analyze(workspace: str, kind: str = "history", profile_number: int = 0,
                          star: str = "") -> str:
        """Extract key properties from a run, as JSON. Two kinds:

        - `kind="history"` (default): evolutionary state from history.data — final model/age/L/Teff,
          core masses, central abundances, current convective core, a coarse phase guess, and the
          TAMS transition. With `star="binary"` it instead summarizes the **orbital** evolution
          (period, separation, masses, mass-transfer onset) from binary_history.data.
        - `kind="profile"`: one saved profile — convective/overshoot/semiconvective/thermohaline
          mixing zones (as mass intervals), central abundances, He/CO core estimates, burning regions.

        For a **binary** run, set `star` to `"1"`/`"2"` for a component (or `"binary"` for the orbit
        with kind="history").

        Args:
            workspace: the work-folder path.
            kind: 'history' or 'profile'.
            profile_number: (profile) which saved profile (0 = latest).
            star: binary component selector — '1', '2', 'binary' (history only), or '' (single-star).
        """
        env = build_env_context()
        k = kind.strip().lower()
        if k == "profile":
            return json.dumps(analysis.analyze_profile(env, workspace, profile_number, star), indent=2)
        if k == "history":
            return json.dumps(analysis.analyze_history(env, workspace, star), indent=2)
        return json.dumps({"error": f"Unknown kind '{kind}'. Use 'history' or 'profile'."}, indent=2)

    @mcp.tool()
    def mesa_data_library(library: str = "", name: str = "") -> str:
        """Browse MESA's bundled data libraries under `$MESA_DIR/data` (read-only), as JSON.

        With no `library`, lists every library (atmospheres, chem/isotopes, EOS, opacities, nuclear
        networks, rates, …) with a short description and file count. With a `library`, dedicated
        parsers:
        - `library="net"` — nuclear networks. No `name` → list; `name="approx21"` → its isotopes +
          reaction handles (includes resolved).
        - `library="solar"` — solar abundances. `name="lodders09"` (default) / `"lodders03"`.
        - `library="isotope"` — one isotope's properties (`name="c12"`).
        - `library="colors"` — synthetic photometry. `name="filters"` / `name="models"`.

        Any other `data/*_data` subdir returns a structured inventory (e.g. `kap`, `eosDT`, `atm`,
        `ionization`, `roche`); the large EOS/opacity grids are inventoried, not numerically parsed.

        Args:
            library: '' to list all, else 'net', 'solar', 'isotope', 'colors', or a data subdir name.
            name: the specific item within the library (network/pattern/isotope/selector).
        """
        env = build_env_context()
        if not library.strip():
            return json.dumps(data_libs.list_libraries(env), indent=2)
        return json.dumps(data_libs.load_data(env, library, name), indent=2)

    @mcp.tool()
    def mesa_data_rate(action: str = "get", reaction: str = "", t9: float = 0.5,
                       workspace: str = "", factor: float = 1.0) -> str:
        """Query or scale a MESA nuclear reaction rate (JINA REACLIB), as JSON. Two actions:

        - `action="get"` (default): look up a reaction by handle (e.g. `r_c12_c12_to_he4_ne20`) and
          return its REACLIB fit set(s) **evaluated at `t9`** — fit coefficients, source→citation,
          Q-value, and rate. For a branching ratio, call each channel and compare `total_rate`. If
          the handle isn't found, `suggestions` lists near matches (a missing set may be a
          weak/tabulated rate).
        - `action="set_factor"`: scale a reaction's rate in a run by `factor`, hiding the
          `special_rate_factor` array syntax — patches `reaction_for_special_factor(i)` /
          `special_rate_factor(i)` / `num_special_rate_factors` into &controls (format-preserving,
          backed up). Requires `workspace` + `reaction`.

        Args:
            action: "get" or "set_factor".
            reaction: the MESA reaction handle (as in reactions.list).
            t9: (get) temperature in 10^9 K (default 0.5).
            workspace: (set_factor) the work-folder path, or the inlist file holding &controls.
            factor: (set_factor) the multiplier (1.0 = unchanged).
        """
        env = build_env_context()
        act = action.strip().lower()
        if act == "get":
            if not reaction:
                return json.dumps({"error": "action='get' requires a reaction handle."}, indent=2)
            return json.dumps(rates.get_reaction_rate(env, reaction, t9), indent=2)
        if act in ("set_factor", "set", "factor"):
            if not workspace or not reaction:
                return json.dumps({"error": "action='set_factor' requires workspace and reaction."},
                                  indent=2)
            return json.dumps(rates.set_rate_factor(env, workspace, reaction, factor), indent=2)
        return json.dumps({"error": f"Unknown action '{action}'. Use 'get' or 'set_factor'."}, indent=2)
