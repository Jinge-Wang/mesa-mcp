"""Confirmation-gated removal of a workspace's run artifacts.

Targets only run *output* — ``LOGS*/``, ``photos*/``, ``png/``, top-level PGSTAR ``*.png``, and the
detached-run state files (``mesa_run.log``, ``.mesa_run.json``, ``.mesa_run.exit``). It NEVER touches
inlists, ``src/``, ``run_star_extras.f90``, ``make/``, or anything else, and refuses any path inside
``$MESA_DIR``.

Two-step safety: with ``confirm=False`` (default) it only reports what *would* be removed (a dry run);
only ``confirm=True`` deletes. **Do not clean between phases of a multi-phase run** — later phases load
models/photos saved by earlier ones.
"""
from __future__ import annotations

import glob
import os
import shutil

from . import config
from .runner import EXIT_NAME, LOG_NAME, STATE_NAME, _is_within


def _dir_size(path: str) -> int:
    total = 0
    for root, _dirs, files in os.walk(path):
        for f in files:
            try:
                total += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total


def _human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _targets(ws: str) -> list:
    """Collect the run-artifact paths present in ``ws`` (dirs first, then state files)."""
    paths = []
    for logs in sorted(glob.glob(os.path.join(ws, "LOGS*"))):
        if os.path.isdir(logs):
            paths.append(logs)
    for name in ("photos", "photos1", "photos2", "png", "plots"):
        p = os.path.join(ws, name)
        if os.path.isdir(p):
            paths.append(p)
    for name in (LOG_NAME, STATE_NAME, EXIT_NAME):
        p = os.path.join(ws, name)
        if os.path.exists(p):
            paths.append(p)
    paths.extend(sorted(glob.glob(os.path.join(ws, "*.png"))))
    return paths


def clean_workspace(env: dict, workspace: str, confirm: bool = False) -> dict:
    """Remove (or, with ``confirm=False``, just list) a workspace's run artifacts."""
    ws = os.path.abspath(os.path.expanduser(workspace))
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    if _is_within(ws, mesa_dir):
        return {"error": f"Refusing to clean inside the MESA install ({mesa_dir})."}

    items = []
    for t in _targets(ws):
        is_dir = os.path.isdir(t)
        size = _dir_size(t) if is_dir else (os.path.getsize(t) if os.path.exists(t) else 0)
        items.append({"path": t, "is_dir": is_dir, "size": _human(size)})

    if not items:
        return {"cleaned": False, "workspace": ws, "removed": [],
                "note": "No run artifacts to remove."}

    if not confirm:
        return {"cleaned": False, "workspace": ws, "dry_run": True, "would_remove": items,
                "note": ("Dry run — nothing deleted. Re-call with confirm=True to remove these. "
                         "Do NOT clean between phases of a multi-phase run (later phases reuse "
                         "models saved earlier).")}

    removed, errors = [], []
    for it in items:
        try:
            if it["is_dir"]:
                shutil.rmtree(it["path"])
            else:
                os.remove(it["path"])
            removed.append(it["path"])
        except OSError as e:
            errors.append(f"{it['path']}: {e}")
    return {"cleaned": True, "workspace": ws, "removed": removed, "errors": errors}
