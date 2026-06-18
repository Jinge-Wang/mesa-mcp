"""Provision MESA work folders OUTSIDE the read-only MESA installation.

Copies a baseline — the standard ``star``/``binary`` work template, or a verified
test-suite case — into a sibling workspace directory, excluding run outputs (LOGS, photos,
caches). The agent then edits the inlists (verifying controls with ``mesa_get_option``) and
compiles/runs via ``mesa_execute_shell``. Nothing is ever written inside ``$MESA_DIR``.
"""
from __future__ import annotations

import glob
import os
import re
import shutil

from . import config

# Run outputs and build artifacts that should not be copied into a fresh workspace.
_EXCLUDE = shutil.ignore_patterns(
    "LOGS", "LOGS_*", "photos", "photos_*", ".mesa_temp_cache",
    "png", "*.o", "*.mod.tmp", ".git", ".DS_Store",
)

_TEST_SUITE_MODULES = ("star", "binary", "astero")


def _is_within(child: str, parent: str) -> bool:
    if not parent:
        return False
    c = os.path.realpath(child)
    p = os.path.realpath(parent)
    return c == p or c.startswith(p + os.sep)


def resolve_baseline(env: dict, baseline: str):
    """Resolve a baseline to (source_path, kind). kind is the module: star/binary/astero.

    Accepts ``work``/``star`` (the star work template), ``binary`` (the binary work
    template), or any test-suite case name (searched across star/binary/astero).
    Returns (None, error_message) on failure.
    """
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if not mesa_dir:
        return None, "MESA_DIR is not set; cannot locate a baseline."

    b = (baseline or "work").strip()
    if b in ("work", "star", "star/work"):
        src = os.path.join(mesa_dir, "star", "work")
        return (src, "star") if os.path.isdir(src) else (None, "star/work template not found.")
    if b in ("binary", "binary/work"):
        src = os.path.join(mesa_dir, "binary", "work")
        return (src, "binary") if os.path.isdir(src) else (None, "binary/work template not found.")

    for module in _TEST_SUITE_MODULES:
        src = os.path.join(mesa_dir, module, "test_suite", b)
        if os.path.isdir(src):
            return src, module
    return None, (f"Unknown baseline '{baseline}'. Use 'work', 'binary', or a test-suite case "
                  "name from mesa_fetch_test_suite_index.")


def create_workspace(env: dict, name: str, baseline: str = "work", dest: str = "") -> dict:
    """Provision a work folder from a baseline, outside ``$MESA_DIR``. Returns a summary dict."""
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    src, kind = resolve_baseline(env, baseline)
    if src is None:
        return {"error": kind}

    if dest.strip():
        dest_dir = os.path.abspath(os.path.expanduser(dest.strip()))
    else:
        safe = re.sub(r"[^A-Za-z0-9._-]", "_", (name or "").strip()) or "run"
        dest_dir = os.path.join(config.workspace_root(), safe)

    if _is_within(dest_dir, mesa_dir):
        return {"error": (f"Refusing to create a workspace inside the MESA install ({mesa_dir}). "
                          "Choose a path outside the MESA tree.")}
    if os.path.exists(dest_dir) and os.listdir(dest_dir):
        return {"error": f"Destination already exists and is not empty: {dest_dir}. Pick another name."}

    try:
        shutil.copytree(src, dest_dir, ignore=_EXCLUDE, dirs_exist_ok=True)
    except OSError as e:
        return {"error": f"Copy failed: {e}"}

    inlists = sorted(os.path.basename(p) for p in glob.glob(os.path.join(dest_dir, "inlist*")))
    return {
        "name": name,
        "kind": kind,
        "baseline": baseline,
        "source": src,
        "dest": dest_dir,
        "inlists": inlists,
        "entries": sorted(os.listdir(dest_dir)),
    }


def list_workspaces() -> dict:
    """List provisioned work folders under the workspace root."""
    root = config.workspace_root()
    workspaces = []
    for n in sorted(os.listdir(root)):
        d = os.path.join(root, n)
        if not os.path.isdir(d):
            continue
        workspaces.append({
            "name": n,
            "path": d,
            "has_LOGS": os.path.isdir(os.path.join(d, "LOGS")) or bool(glob.glob(os.path.join(d, "LOGS_*"))),
            "inlists": sorted(os.path.basename(p) for p in glob.glob(os.path.join(d, "inlist*"))),
        })
    return {"root": root, "workspaces": workspaces}
