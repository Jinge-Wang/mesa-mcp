"""Visualization: surface PGSTAR plot images, and enable headless file output.

On a headless host (VS Code / remote / no X11), PGSTAR's on-screen window cannot open — so
the simulation can't be watched live that way. The fix is PGSTAR **file output**: have MESA
write plot PNGs to disk during the run (``*_file_flag`` / ``*_file_dir``), then surface the
newest image. ``find_plots``/``latest_plot`` locate run output; ``enable_file_output`` flips
the plots already defined as windows (``*_win_flag``) to also write files.
"""
from __future__ import annotations

import glob
import os
import re

from . import inlist, inlist_resolver

_IMG_EXTS = (".png", ".svg", ".jpg", ".jpeg", ".gif")
# Don't recurse into these (run state, build, source, committed reference images).
_SKIP_DIRS = {"LOGS", "photos", ".mesa_temp_cache", "make", "src", "docs", ".git"}
_MODEL_RE = re.compile(r"(\d{3,})")
_WIN_FLAG_RE = re.compile(r"^(?P<plot>\w+)_win_flag$")


def find_plots(workspace: str, limit: int = 200) -> dict:
    """Return plot images found under a workspace, newest first (run output, not LOGS/docs)."""
    ws = os.path.abspath(os.path.expanduser(workspace))
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    images = []
    for root, dirs, files in os.walk(ws):
        dirs[:] = [d for d in dirs if d not in _SKIP_DIRS and not d.startswith("LOGS")]
        for fn in files:
            if not fn.lower().endswith(_IMG_EXTS):
                continue
            path = os.path.join(root, fn)
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            m = _MODEL_RE.search(fn)
            images.append({
                "path": path,
                "name": fn,
                "mtime": round(mtime, 1),
                "model": int(m.group(1)) if m else None,
            })
    images.sort(key=lambda x: x["mtime"], reverse=True)
    return {"workspace": ws, "count": len(images), "plots": images[:limit]}


def latest_plot(workspace: str) -> dict:
    """Return the single newest plot image in a workspace (or an error/empty note)."""
    res = find_plots(workspace)
    if res.get("error"):
        return res
    if not res["plots"]:
        return {"error": ("No plot images found. Enable PGSTAR file output "
                          "(mesa_plot_pgstar) and run the simulation first.")}
    return {"latest": res["plots"][0], "total": res["count"]}


def _read_lines(path: str) -> list:
    try:
        return open(path, "r", encoding="utf-8", errors="replace").read().splitlines()
    except OSError:
        return []


def _file_with_namelist(files: list, namelist: str) -> "str | None":
    for f in files:
        if inlist._find_namelist(_read_lines(f), namelist):
            return f
    return None


def _enable_namelist(env, files, plot_nl, flag_nl, flag_name, plot_filter, out_dir, interval, changes):
    """Enable file output for one plotting namelist (``pgstar`` or ``pgbinary``).

    Sets the master ``flag_name`` in ``&flag_nl`` (e.g. ``pgstar_flag`` in ``&star_job``) and, for
    each window plot (``<plot>_win_flag``) or each name in ``plot_filter``, the matching
    ``<plot>_file_flag``/``_file_dir``/``_file_interval`` in ``&plot_nl``. Returns a summary or None
    if this workspace has no ``&plot_nl`` namelist.
    """
    win_by_file: dict = {}
    declared = []
    for f in files:
        lines = _read_lines(f)
        if inlist._find_namelist(lines, plot_nl):
            declared.append(f)
        for s in inlist.read_settings(f):
            m = _WIN_FLAG_RE.match(s["name"])
            if m and s["namelist"] == plot_nl:
                win_by_file.setdefault(f, []).append(m.group("plot"))
    if not declared:
        return None

    target = (max(win_by_file, key=lambda f: len(win_by_file[f])) if win_by_file else declared[0])
    plot_list = plot_filter or list(dict.fromkeys(win_by_file.get(target, [])))
    summary = {"namelist": plot_nl, "file": os.path.basename(target),
               "plots": list(plot_list)}
    if not plot_list:
        summary["note"] = (f"no {plot_nl} window plots (*_win_flag) found to convert; "
                           "pass plots='Grid1' (or whichever this inlist defines).")
        return summary

    def _apply(path, name, value, nl):
        r = inlist.set_option(env, path, name, value, nl)
        changes.append({"file": os.path.basename(path), "control": name,
                        "result": r.get("action") or r.get("error")})

    flag_file = _file_with_namelist(files, flag_nl)
    if flag_file:
        _apply(flag_file, flag_name, ".true.", flag_nl)
    for plot in dict.fromkeys(plot_list):
        _apply(target, f"{plot}_file_flag", ".true.", plot_nl)
        _apply(target, f"{plot}_file_dir", f"'{out_dir}'", plot_nl)
        _apply(target, f"{plot}_file_interval", str(interval), plot_nl)
    return summary


def enable_file_output(env: dict, workspace: str, plots: str = "", out_dir: str = "png",
                       interval: int = 10) -> dict:
    """Turn on headless plot **file** output in a workspace's inlists.

    Enables ``&pgstar`` (``pgstar_flag`` in ``&star_job``) and, for a **binary** run, also
    ``&pgbinary`` (``pgbinary_flag`` in ``&binary_job``). For each plot defined as a window
    (``<plot>_win_flag``) — or each name in ``plots`` — it sets ``<plot>_file_flag`` /
    ``<plot>_file_dir`` / ``<plot>_file_interval``.
    """
    ws = os.path.abspath(os.path.expanduser(workspace))
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    files = [f for f in sorted(glob.glob(os.path.join(ws, "inlist*"))) if not f.endswith(".bak")]
    if not files:
        return {"error": "No inlist files in this workspace."}

    try:
        kind = inlist_resolver.layout(ws).get("kind")
    except Exception:
        kind = "star"
    groups = [("pgstar", "star_job", "pgstar_flag")]
    if kind == "binary":
        groups.append(("pgbinary", "binary_job", "pgbinary_flag"))

    plot_filter = [p for p in re.split(r"[,\s]+", plots.strip()) if p]
    changes: list = []
    enabled = []
    for plot_nl, flag_nl, flag_name in groups:
        s = _enable_namelist(env, files, plot_nl, flag_nl, flag_name, plot_filter,
                             out_dir, interval, changes)
        if s:
            enabled.append(s)
    if not enabled:
        return {"error": "No &pgstar (or &pgbinary) namelist found in this workspace."}
    return {"workspace": ws, "kind": kind, "out_dir": out_dir, "enabled": enabled, "changes": changes}
