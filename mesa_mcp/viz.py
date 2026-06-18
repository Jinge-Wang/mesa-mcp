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

from . import inlist

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
                          "(mesa_enable_pgstar_file_output) and run the simulation first.")}
    return {"latest": res["plots"][0], "total": res["count"]}


def enable_file_output(env: dict, workspace: str, plots: str = "", out_dir: str = "png",
                       interval: int = 10) -> dict:
    """Turn on PGSTAR file output in a workspace's inlists.

    Sets ``pgstar_flag`` in the &star_job inlist and, for each plot, ``<plot>_file_flag`` /
    ``<plot>_file_dir`` / ``<plot>_file_interval`` in the &pgstar inlist. If ``plots`` is empty,
    auto-detects the plots already defined as windows (``<plot>_win_flag``).
    """
    ws = os.path.abspath(os.path.expanduser(workspace))
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    files = [f for f in sorted(glob.glob(os.path.join(ws, "inlist*"))) if not f.endswith(".bak")]

    star_job_file = None
    pgstar_candidates = []
    win_by_file: dict = {}
    for f in files:
        try:
            lines = open(f, "r", encoding="utf-8", errors="replace").read().splitlines()
        except OSError:
            continue
        if star_job_file is None and inlist._find_namelist(lines, "star_job"):
            star_job_file = f
        if inlist._find_namelist(lines, "pgstar"):
            pgstar_candidates.append(f)
        for s in inlist.read_settings(f):
            m = _WIN_FLAG_RE.match(s["name"])
            if m and s["namelist"] == "pgstar":
                win_by_file.setdefault(f, []).append(m.group("plot"))
    if not pgstar_candidates:
        return {"error": "No inlist with a &pgstar namelist found in this workspace."}

    # Prefer the file that actually defines the plot windows (e.g. inlist_pgstar).
    pgstar_file = (max(win_by_file, key=lambda f: len(win_by_file[f]))
                   if win_by_file else pgstar_candidates[0])

    plot_list = [p for p in re.split(r"[,\s]+", plots.strip()) if p]
    if not plot_list:
        plot_list = list(win_by_file.get(pgstar_file, []))
    if not plot_list:
        return {"error": ("No plots specified and none defined as windows (*_win_flag). "
                          "Pass plots='Grid1' (or whichever your inlist_pgstar defines).")}

    changes = []

    def _apply(path, name, value, nl):
        r = inlist.set_option(env, path, name, value, nl)
        changes.append({"control": name, "result": r.get("action") or r.get("error")})

    if star_job_file:
        _apply(star_job_file, "pgstar_flag", ".true.", "star_job")
    for plot in dict.fromkeys(plot_list):  # dedupe, keep order
        _apply(pgstar_file, f"{plot}_file_flag", ".true.", "pgstar")
        _apply(pgstar_file, f"{plot}_file_dir", f"'{out_dir}'", "pgstar")
        _apply(pgstar_file, f"{plot}_file_interval", str(interval), "pgstar")

    return {
        "workspace": ws,
        "star_job_file": os.path.basename(star_job_file) if star_job_file else None,
        "pgstar_file": os.path.basename(pgstar_file),
        "plots": list(dict.fromkeys(plot_list)),
        "out_dir": out_dir,
        "changes": changes,
    }
