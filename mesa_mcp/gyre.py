"""Run the GYRE stellar-oscillation code on a pulsation model produced by MESA.

GYRE ships under ``$MESA_DIR/gyre`` but is a separate program with its own ``$GYRE_DIR`` and inlist
(``gyre.in``). This drives a standalone GYRE run — ``$GYRE_DIR/bin/gyre <inlist>`` — in a workspace
and parses the text summary of computed modes (frequencies). It requires GYRE to be **built** and
``$GYRE_DIR`` set (or the bundled ``$MESA_DIR/gyre`` built); otherwise it returns clear guidance.
The MESA model must first be written as a GYRE pulsation file (the ``astero`` workflow or
``write_pulse_data_*`` controls). This server does not yet configure that step.
"""
from __future__ import annotations

import os
import subprocess

from . import config


def _gyre_bin(env: dict) -> "str | None":
    """Locate an executable gyre binary from $GYRE_DIR, else the bundled $MESA_DIR/gyre."""
    candidates = []
    gyre_dir = env.get("GYRE_DIR", "")
    if gyre_dir:
        candidates.append(os.path.join(gyre_dir, "bin", "gyre"))
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if mesa_dir:
        candidates.append(os.path.join(mesa_dir, "gyre", "bin", "gyre"))
    for c in candidates:
        if os.path.isfile(c) and os.access(c, os.X_OK):
            return c
    return None


def _parse_summary(path: str, max_modes: int = 50) -> dict:
    """Best-effort parse of a GYRE text summary (column-name header then rows)."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = [ln for ln in f.read().splitlines() if ln.strip()]
    except OSError:
        return {}
    names_idx = None
    for i, ln in enumerate(lines):
        toks = ln.split()
        low = ln.lower()
        if ("freq" in low or "n_pg" in low) and not any(_is_float(t) for t in toks):
            names_idx = i
            break
    if names_idx is None:
        return {}
    names = lines[names_idx].split()
    modes = []
    for ln in lines[names_idx + 1:]:
        vals = ln.split()
        if len(vals) != len(names) or not _is_float(vals[0]):
            continue
        modes.append({n: _coerce(v) for n, v in zip(names, vals)})
        if len(modes) >= max_modes:
            break
    return {"columns": names, "n_modes": len(modes), "modes": modes}


def _is_float(s: str) -> bool:
    try:
        float(s.replace("D", "E").replace("d", "e"))
        return True
    except ValueError:
        return False


def _coerce(v: str):
    try:
        return int(v)
    except ValueError:
        try:
            return float(v.replace("D", "E").replace("d", "e"))
        except ValueError:
            return v


def run_gyre(env: dict, workspace: str, inlist: str = "gyre.in",
             summary_file: str = "", timeout: int = 600) -> dict:
    """Run GYRE in ``workspace`` and parse its mode summary. Bounded/synchronous."""
    ws = os.path.abspath(os.path.expanduser(workspace))
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    gbin = _gyre_bin(env)
    if not gbin:
        return {"error": "GYRE binary not found. Build GYRE (e.g. in $MESA_DIR/gyre) and set "
                         "$GYRE_DIR, then retry. See get_mesa_info's GYRE line."}
    inlist_path = inlist if os.path.isabs(inlist) else os.path.join(ws, inlist)
    if not os.path.isfile(inlist_path):
        return {"error": f"GYRE inlist not found: {inlist_path}. Provide a gyre.in in the workspace."}

    run_env = dict(env)
    run_env.setdefault("GYRE_DIR", os.path.dirname(os.path.dirname(gbin)))
    before = set(os.listdir(ws))
    try:
        proc = subprocess.run([gbin, os.path.basename(inlist_path)], cwd=ws, env=run_env,
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"error": f"GYRE timed out after {timeout}s. Run it via mesa_execute_shell if it "
                         "legitimately needs longer."}
    except Exception as e:
        return {"error": f"Failed to launch GYRE: {e}"}

    out = {"gyre_bin": gbin, "inlist": inlist_path, "returncode": proc.returncode,
           "ok": proc.returncode == 0,
           "stdout_tail": proc.stdout.splitlines()[-20:] if proc.stdout else [],
           "stderr_tail": proc.stderr.splitlines()[-10:] if proc.stderr else []}

    # Locate the summary file: the one named, else a new *.txt/*summary* created by the run.
    cand = None
    if summary_file:
        p = summary_file if os.path.isabs(summary_file) else os.path.join(ws, summary_file)
        cand = p if os.path.isfile(p) else None
    if not cand:
        new = [f for f in os.listdir(ws) if f not in before]
        sums = [f for f in new if "summary" in f.lower() or f.endswith(".txt")]
        if sums:
            cand = os.path.join(ws, max(sums, key=lambda f: os.path.getmtime(os.path.join(ws, f))))
    if cand:
        out["summary_file"] = cand
        out.update({k: v for k, v in _parse_summary(cand).items()})
    elif out["ok"]:
        out["note"] = "GYRE finished but no text summary file was found — check the &ad_output / " \
                      "&nad_output summary_file setting in the inlist."
    return out
