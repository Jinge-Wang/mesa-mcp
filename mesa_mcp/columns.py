"""MESA output columns: parse *_columns.list reference, and read run data slices.

The master ``$MESA_DIR/star/defaults/{history,profile}_columns.list`` files list every
available output column (commented = available, uncommented = selected by default) with a
short doc. ``read_history`` parses a run's ``LOGS/history.data`` with the standard library
and returns a small, column-selected, downsampled slice — never the whole table.
"""
from __future__ import annotations

import glob
import os
import re

from . import config

# A column line: optional leading '!', a name, then optional ' ! doc'.
_COL_RE = re.compile(
    r"^(?P<indent>\s*)(?P<bang>!)?\s*(?P<name>[A-Za-z_]\w*(?:\([^)]*\))?)\s*(?:!\s*(?P<doc>.*))?$"
)
# Per-isotope columns are written as `prefix <iso>` (e.g. `center h1`), producing the output
# column `center_h1`. Gated to an isotope-like second token so prose can't match.
_TWO_TOKEN_RE = re.compile(
    r"^(?P<indent>\s*)(?P<bang>!)?\s*(?P<a>[A-Za-z_]\w*)\s+(?P<b>[A-Za-z]{1,3}\d{0,3})\s*(?:!\s*(?P<doc>.*))?$"
)
_KINDS = {"history": "history_columns.list", "profile": "profile_columns.list"}
_DEFAULT_HISTORY = ["model_number", "star_age", "log_L", "log_Teff", "log_R",
                    "star_mass", "center_h1", "center_he4"]

_MEMO: dict = {}


def _master_path(mesa_dir: str, kind: str) -> "str | None":
    fn = _KINDS.get(kind)
    return os.path.join(mesa_dir, "star", "defaults", fn) if (mesa_dir and fn) else None


def parse_columns(text: str) -> list:
    """Parse a *_columns.list body into [{name, selected, doc}] (skips prose/headers)."""
    cols = []
    for ln in text.splitlines():
        s = ln.lstrip()
        if not s or s.startswith(("!#", "!-", "!=", "!*")):
            continue
        m = _COL_RE.match(ln)
        if m:
            cols.append({
                "name": m.group("name"),
                "selected": not m.group("bang"),
                "doc": (m.group("doc") or "").strip(),
            })
            continue
        m2 = _TWO_TOKEN_RE.match(ln)
        if m2:
            cols.append({
                "name": f"{m2.group('a')}_{m2.group('b')}",
                "selected": not m2.group("bang"),
                "doc": (m2.group("doc") or "").strip(),
            })
    return cols


def get_columns(env: dict, kind: str) -> list:
    """Return the parsed master column list for 'history' or 'profile' (memoized)."""
    path = _master_path(env.get(config.MESA_DIR_ENV, ""), kind)
    if not path or not os.path.isfile(path):
        return []
    st = os.stat(path)
    sig = (st.st_size, round(st.st_mtime, 3))
    memo = _MEMO.get(path)
    if memo and memo[0] == sig:
        return memo[1]
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        cols = parse_columns(f.read())
    _MEMO[path] = (sig, cols)
    return cols


def lookup(env: dict, name: str, kind: str = "history") -> dict:
    """Look up an output column by name; returns {'exact', 'related', 'kind', 'total'}."""
    cols = get_columns(env, kind)
    t = name.strip().lower()
    exact = [c for c in cols if c["name"].lower() == t]
    related = [] if exact else [c for c in cols if t in c["name"].lower()][:25]
    return {"exact": exact, "related": related, "kind": kind, "total": len(cols)}


def _resolve_history_file(path: str) -> "str | None":
    if os.path.isfile(path):
        return path
    for cand in (os.path.join(path, "LOGS", "history.data"),
                 os.path.join(path, "history.data")):
        if os.path.isfile(cand):
            return cand
    matches = sorted(glob.glob(os.path.join(path, "LOGS*", "history.data")))
    return matches[0] if matches else None


def load_mesa_data(path: str, file_type: "str | None" = None):
    """Canonical numeric loader: return a ``mesa_reader.MesaData`` for a history/profile file.

    This is the data path for the analysis/plotting tools (numpy-backed columns via
    ``md.data(name)`` and names via ``md.bulk_names``). ``mesa_reader`` is imported lazily so the
    stdlib ``read_history`` slicer keeps working without the dependency. ``file_type`` is
    ``'history'``/``'profile'`` (auto-detected when None). Raises RuntimeError if unavailable.
    """
    p = os.path.abspath(os.path.expanduser(path))
    resolved = _resolve_history_file(p) if (file_type != "profile") else (p if os.path.isfile(p) else None)
    resolved = resolved or (p if os.path.isfile(p) else None)
    if not resolved:
        raise RuntimeError(f"No data file found at or under {p}.")
    try:
        from mesa_reader import MesaData
    except ImportError as e:
        raise RuntimeError("mesa_reader is not installed — run `uv add mesa_reader`, or use "
                           "read_history for a stdlib slice.") from e
    return MesaData(resolved, file_type=file_type)


def _coerce(v: str):
    """Best-effort numeric coercion so the value serializes as a JSON number, not a string."""
    try:
        i = int(v)
        return i
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        return v


def latest_model(env: dict, path: str) -> dict:
    """Return the most recent history.data row as an aligned {column: value} dict (all columns).

    Values are numerically coerced where possible. Returns {} if no usable history exists yet.
    """
    p = os.path.abspath(os.path.expanduser(path))
    data_file = _resolve_history_file(p)
    if not data_file:
        return {}
    with open(data_file, "r", encoding="utf-8", errors="replace") as f:
        nonblank = [ln for ln in f.read().splitlines() if ln.strip()]
    if len(nonblank) < 6:
        return {}
    names = nonblank[4].split()
    vals = nonblank[-1].split()
    return {n: _coerce(vals[i]) if i < len(vals) else None for i, n in enumerate(names)}


def read_history(env: dict, path: str, columns: "list | None" = None,
                 last_n: int = 20, every: int = 1) -> dict:
    """Read a run's history.data and return a selected, downsampled slice.

    The MESA .data layout (blank lines removed) is: header numbers / header names / header
    values / data numbers / data names / data rows.
    """
    p = os.path.abspath(os.path.expanduser(path))
    data_file = _resolve_history_file(p)
    if not data_file:
        return {"error": f"No history.data found at or under {p} (has the run produced output?)."}

    with open(data_file, "r", encoding="utf-8", errors="replace") as f:
        nonblank = [ln for ln in f.read().splitlines() if ln.strip()]
    if len(nonblank) < 6:
        return {"error": f"{data_file} has a header but no data rows yet."}

    names = nonblank[4].split()
    data_lines = nonblank[5:]
    index = {n: i for i, n in enumerate(names)}

    requested = columns or [c for c in _DEFAULT_HISTORY if c in index] or names[:8]
    selected = [c for c in requested if c in index]
    missing = [c for c in requested if c not in index]

    every = max(1, int(every))
    last_n = max(1, int(last_n))
    sampled = data_lines[::every][-last_n:]
    rows = []
    for ln in sampled:
        vals = ln.split()
        rows.append([vals[index[c]] if index[c] < len(vals) else "" for c in selected])

    return {
        "file": data_file,
        "total_models": len(data_lines),
        "columns": selected,
        "missing": missing,
        "rows": rows,
        "shown": len(rows),
        "every": every,
    }
