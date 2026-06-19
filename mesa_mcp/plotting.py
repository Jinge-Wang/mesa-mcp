"""Render MESA history/profile plots to PNG with matplotlib (headless ``Agg`` backend).

A dedicated, token-cheap alternative to having the agent hand-write plotting scripts. Built on
``columns.load_mesa_data`` (the mesa_reader-backed loader). Plots are written to ``<workspace>/plots``
and returned as a path; the tool layer also surfaces them inline.

Presets:
- history ``hr`` — the classic HR diagram (log L vs log Teff, Teff axis inverted). The conventions
  (inverted Teff axis, typical ranges) follow A. Gautschy's *SimpleMesaHRD* (Zenodo 10.5281/zenodo.2619182);
  this is an independent mesa_reader/matplotlib reimplementation, with thanks to that reference.
- profile ``abundance`` — mass-fraction profiles of the common isotopes vs mass coordinate (log y).
"""
from __future__ import annotations

import glob
import os

from . import columns

# Isotopes drawn by the abundance preset, in rough nucleosynthesis order, when present.
_ABUND_ISOS = ["h1", "he3", "he4", "c12", "n14", "o16", "ne20", "mg24", "si28", "fe56"]


def _plots_dir(ws: str) -> str:
    d = os.path.join(ws, "plots")
    os.makedirs(d, exist_ok=True)
    return d


def _pyplot():
    """Import matplotlib with the non-interactive Agg backend (headless-safe)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _resolve_profile(ws: str, profile_number: int = 0) -> "str | None":
    """Resolve a profile.data path in a workspace (latest by profile number if 0)."""
    cands = sorted(glob.glob(os.path.join(ws, "LOGS*", "profile*.data"))
                   + glob.glob(os.path.join(ws, "profile*.data")))
    if not cands:
        return None
    if profile_number:
        for c in cands:
            base = os.path.basename(c)
            digits = "".join(ch for ch in base if ch.isdigit())
            if digits and int(digits) == profile_number:
                return c
        return None
    # latest = highest profile number
    def _num(p):
        d = "".join(ch for ch in os.path.basename(p) if ch.isdigit())
        return int(d) if d else -1
    return max(cands, key=_num)


def plot_history(env: dict, workspace: str, x: str = "model_number", y: str = "log_L",
                 preset: str = "", logx: bool = False, logy: bool = False) -> dict:
    """Plot one or more history columns (``y`` may be comma-separated) versus ``x``."""
    ws = os.path.abspath(os.path.expanduser(workspace))
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    try:
        md = columns.load_mesa_data(ws, file_type="history")
    except RuntimeError as e:
        return {"error": str(e)}

    invert_x = False
    title = None
    if preset.lower() == "hr":
        x, y, invert_x = "log_Teff", "log_L", True
        title = "HR diagram"

    ys = [c.strip() for c in y.split(",") if c.strip()]
    if not md.in_data(x):
        return {"error": f"Column '{x}' not in history.data.", "available_hint": "use mesa_get_output_column"}
    missing = [c for c in ys if not md.in_data(c)]
    ys = [c for c in ys if md.in_data(c)]
    if not ys:
        return {"error": f"None of the requested y columns are in history.data (missing {missing})."}

    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6, 5))
    xv = md.data(x)
    for c in ys:
        ax.plot(xv, md.data(c), lw=1.3, label=c)
    if invert_x:
        ax.invert_xaxis()
    if logx:
        ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel(x)
    ax.set_ylabel(ys[0] if len(ys) == 1 else "value")
    if len(ys) > 1:
        ax.legend(fontsize=8)
    if title:
        ax.set_title(title)
    ax.grid(alpha=0.3)
    fig.tight_layout()

    name = "hr.png" if preset.lower() == "hr" else f"history_{'_'.join(ys)}_vs_{x}.png"
    out = os.path.join(_plots_dir(ws), name)
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return {"path": out, "x": x, "y": ys, "missing": missing, "preset": preset or None,
            "n_points": int(len(xv))}


def plot_profile(env: dict, workspace: str, x: str = "mass", y: str = "logRho",
                 preset: str = "", profile_number: int = 0,
                 logx: bool = False, logy: bool = False) -> dict:
    """Plot profile columns (``y`` comma-separated) versus ``x`` for one saved profile."""
    ws = os.path.abspath(os.path.expanduser(workspace))
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    pf = _resolve_profile(ws, profile_number)
    if not pf:
        return {"error": f"No profile*.data found in {ws}/LOGS (save profiles first)."}
    try:
        md = columns.load_mesa_data(pf, file_type="profile")
    except RuntimeError as e:
        return {"error": str(e)}

    title = None
    if preset.lower() in ("abundance", "abundances"):
        y = ",".join(i for i in _ABUND_ISOS if md.in_data(i))
        logy, title = True, "Abundance profile"

    if not md.in_data(x):
        return {"error": f"Column '{x}' not in this profile."}
    ys = [c.strip() for c in y.split(",") if c.strip()]
    missing = [c for c in ys if not md.in_data(c)]
    ys = [c for c in ys if md.in_data(c)]
    if not ys:
        return {"error": f"None of the requested y columns are in the profile (missing {missing})."}

    plt = _pyplot()
    fig, ax = plt.subplots(figsize=(6, 5))
    xv = md.data(x)
    for c in ys:
        ax.plot(xv, md.data(c), lw=1.3, label=c)
    if logx:
        ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
        if title:  # abundance preset: keep a sensible floor
            ax.set_ylim(1e-6, 1.5)
    ax.set_xlabel(x)
    ax.set_ylabel(ys[0] if len(ys) == 1 else "mass fraction" if title else "value")
    if len(ys) > 1:
        ax.legend(fontsize=8, ncol=2)
    if title:
        ax.set_title(f"{title} — {os.path.basename(pf)}")
    ax.grid(alpha=0.3)
    fig.tight_layout()

    tag = "abundance" if title else f"{'_'.join(ys)}_vs_{x}"
    out = os.path.join(_plots_dir(ws), f"profile_{tag}.png")
    fig.savefig(out, dpi=120)
    plt.close(fig)
    return {"path": out, "profile": os.path.basename(pf), "x": x, "y": ys,
            "missing": missing, "preset": preset or None, "n_zones": int(len(xv))}
