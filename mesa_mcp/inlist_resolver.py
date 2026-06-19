"""Resolve MESA's inlist chain to learn the *real* filenames and output dirs a run uses.

MESA hardcodes neither inlist names nor output paths. The driver picks an **entry inlist** via
``resolve_inlist_fname`` (command-line arg → ``MESA_INLIST`` env var → default ``'inlist'``), then
assembles each namelist by recursively following ``read_extra_<ns>_inlist(i)`` +
``extra_<ns>_inlist_name(i)`` (later reads override earlier ones — last writer wins). Output
locations are ordinary controls inside that chain:

- star ``&controls``: ``log_directory`` (def ``LOGS``), ``star_history_name`` (def ``history.data``),
  ``photo_directory`` (def ``photos``), ``profile_data_prefix`` (def ``profile``).
- binary ``&binary_controls``: ``history_name`` (def ``binary_history.data``), ``log_directory``
  (def ``.``); ``&binary_job`` ``inlist_names(1..2)`` → the two component inlists (def
  ``inlist1``/``inlist2``), each then resolved as a normal star inlist.

This module is **read-only**. The telemetry / runner / viz / inlist tools consume :func:`layout`
so they follow whatever names a workspace actually uses instead of assuming ``inlist1``/``LOGS1``.
``env`` is only needed to honor ``MESA_INLIST``; everything else is read from the workspace inlists.
"""
from __future__ import annotations

import os
import re

from . import inlist

_MAX_DEPTH = 12  # guards against pathological / circular extra-inlist chains
# An entry inlist named on a run line: ./star <inlist>, ./binary <inlist>, or the test-suite
# helper `do_one <inlist> ...` (multi-phase cases). Captures the inlist filename.
_ARG_RE = re.compile(r"(?:\./(?:star|binary)|do_one)\s+(\S+)")
_ASSIGN_MEMO: dict = {}


def _unquote(v: str) -> str:
    v = (v or "").strip()
    if len(v) >= 2 and v[0] in "'\"" and v[-1] == v[0]:
        return v[1:-1]
    return v


def _is_true(v: str) -> bool:
    return _unquote(v).strip().lower() in (".true.", "true", "t")


def _path(workspace: str, fname: str) -> str:
    return fname if os.path.isabs(fname) else os.path.join(workspace, fname)


def _assignments(workspace: str, fname: str, namelist: str) -> list:
    """Active assignments within ``&namelist`` of one inlist file (memoized by path+mtime)."""
    path = _path(workspace, fname)
    try:
        sig = os.stat(path).st_mtime
    except OSError:
        return []
    memo = _ASSIGN_MEMO.get(path)
    if not memo or memo[0] != sig:
        memo = (sig, inlist.read_settings(path))
        _ASSIGN_MEMO[path] = memo
    return [s for s in memo[1] if s["namelist"] == namelist]


def _file_has_namelist(workspace: str, fname: str, namelist: str) -> bool:
    path = _path(workspace, fname)
    if not os.path.isfile(path):
        return False
    try:
        lines = open(path, "r", encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return False
    return inlist._find_namelist(lines, namelist) is not None


def chain_for(workspace: str, entry: str, namelist: str, _depth: int = 0, _seen=None) -> list:
    """Files contributing to ``&namelist``, in MESA read order (base first, extras 1..n recursively).

    Follows ``read_extra_<namelist>_inlist(i)`` / ``extra_<namelist>_inlist_name(i)``. Cycle- and
    depth-guarded. Returns names relative to ``workspace`` (or absolute if given that way).
    """
    if _seen is None:
        _seen = set()
    path = _path(workspace, entry)
    key = os.path.normpath(path)
    if key in _seen or _depth > _MAX_DEPTH or not os.path.isfile(path):
        return []
    _seen.add(key)
    files = [entry]

    reads: dict = {}
    names: dict = {}
    rprefix = f"read_extra_{namelist}_inlist("
    nprefix = f"extra_{namelist}_inlist_name("
    for s in _assignments(workspace, entry, namelist):
        nm = s["name"]
        if nm.startswith(rprefix) and nm.endswith(")"):
            try:
                reads[int(nm[len(rprefix):-1])] = _is_true(s["value"])
            except ValueError:
                pass
        elif nm.startswith(nprefix) and nm.endswith(")"):
            try:
                names[int(nm[len(nprefix):-1])] = _unquote(s["value"])
            except ValueError:
                pass

    for i in sorted(reads):
        nm = names.get(i)
        if reads.get(i) and nm and nm != "undefined":
            files.extend(chain_for(workspace, nm, namelist, _depth + 1, _seen))
    return files


def effective(workspace: str, entry: str, namelist: str, control: str, default=None):
    """Last value assigned to ``control`` in ``&namelist`` across the resolved chain (or default).

    Matches the control name exactly, so an indexed control like ``inlist_names(1)`` is not
    confused with ``inlist_names(2)``.
    """
    val = default
    for fname in chain_for(workspace, entry, namelist):
        for s in _assignments(workspace, fname, namelist):
            if s["name"] == control:
                val = _unquote(s["value"])
    return val


def owner_file(workspace: str, entry: str, namelist: str) -> "str | None":
    """The chain file where edits to ``&namelist`` belong: the last one that already sets it,
    else the last that declares the ``&namelist`` block, else the deepest chain file."""
    chain = chain_for(workspace, entry, namelist)
    owner = None
    for f in chain:
        if _assignments(workspace, f, namelist):
            owner = f
    if owner:
        return owner
    for f in reversed(chain):
        if _file_has_namelist(workspace, f, namelist):
            return f
    return chain[-1] if chain else None


def option_file(workspace: str, entry: str, namelist: str, control: "str | None" = None) -> "str | None":
    """Which chain file to edit for ``control``: the file currently setting it (edit in place),
    else :func:`owner_file`."""
    if control:
        base = control.split("(")[0]
        for f in chain_for(workspace, entry, namelist):
            for s in _assignments(workspace, f, namelist):
                if s["name"].split("(")[0] == base:
                    return f
    return owner_file(workspace, entry, namelist)


def entry_inlist(workspace: str, env: "dict | None" = None, run_command: str = "./rn") -> str:
    """Resolve the entry inlist the way MESA does: run-command arg → script arg → MESA_INLIST → 'inlist'."""
    ws = os.path.abspath(os.path.expanduser(workspace))
    toks = (run_command or "").split()
    # 1. explicit inlist argument on the run command (e.g. "./rn inlist_foo" / "./star inlist_foo").
    for t in toks[1:]:
        if not t.startswith("-") and os.path.isfile(os.path.join(ws, t)):
            return t
    # 2. an inlist named inside the rn/re script (e.g. "./star inlist_foo" or, for multi-phase
    #    test cases, "do_one inlist_<phase>_header ..."). Use the LAST existing candidate — for a
    #    multi-phase run that's the final phase, the most useful default.
    if toks:
        script = os.path.join(ws, os.path.basename(toks[0]))
        if os.path.isfile(script):
            candidate = None
            try:
                with open(script, "r", encoding="utf-8", errors="replace") as f:
                    for ln in f:
                        m = _ARG_RE.search(ln)
                        if m and os.path.isfile(os.path.join(ws, m.group(1))):
                            candidate = m.group(1)
            except OSError:
                candidate = None
            if candidate:
                return candidate
    # 3. the MESA_INLIST environment variable.
    mi = (env or {}).get("MESA_INLIST") if env else None
    if mi and os.path.isfile(os.path.join(ws, mi)):
        return mi
    return "inlist"


def _star_paths(workspace: str, star_entry: str) -> dict:
    """Resolve one star component's output names from its &controls / &star_job / &pgstar chains."""
    return {
        "entry": star_entry,
        "log_directory": effective(workspace, star_entry, "controls", "log_directory", "LOGS"),
        "history_name": effective(workspace, star_entry, "controls", "star_history_name", "history.data"),
        "photo_directory": effective(workspace, star_entry, "controls", "photo_directory", "photos"),
        "profile_prefix": effective(workspace, star_entry, "controls", "profile_data_prefix", "profile"),
        "star_job_file": owner_file(workspace, star_entry, "star_job"),
        "pgstar_file": owner_file(workspace, star_entry, "pgstar"),
    }


def layout(workspace: str, env: "dict | None" = None, run_command: str = "./rn") -> dict:
    """Resolve the workspace's effective inlist layout and output locations.

    Returns ``{"kind": "star", "entry", "star": {...}}`` or
    ``{"kind": "binary", "entry", "stars": {"1": {...}, "2": {...}}, "binary": {...}}``.
    All directory/file names are the *resolved* values (what MESA will actually use), with MESA's
    documented defaults as fallback when a control isn't set.
    """
    ws = os.path.abspath(os.path.expanduser(workspace))
    entry = entry_inlist(ws, env, run_command)
    is_binary = any(_file_has_namelist(ws, f, "binary_job")
                    for f in (chain_for(ws, entry, "binary_job") or [entry]))
    if is_binary:
        i1 = effective(ws, entry, "binary_job", "inlist_names(1)", "inlist1")
        i2 = effective(ws, entry, "binary_job", "inlist_names(2)", "inlist2")
        return {
            "kind": "binary",
            "entry": entry,
            "stars": {"1": _star_paths(ws, i1), "2": _star_paths(ws, i2)},
            "binary": {
                "history_name": effective(ws, entry, "binary_controls", "history_name", "binary_history.data"),
                "log_directory": effective(ws, entry, "binary_controls", "log_directory", "."),
                "binary_job_file": owner_file(ws, entry, "binary_job"),
                "pgbinary_file": owner_file(ws, entry, "pgbinary"),
            },
        }
    return {"kind": "star", "entry": entry, "star": _star_paths(ws, entry)}
