"""Extract key stellar properties from a run's history/profile data (mesa_reader + numpy).

``analyze_history`` summarizes the evolutionary state (final model, core masses, central
abundances, mixing regions, an evolutionary-phase guess, and key transitions). ``analyze_profile``
locates convective/overshoot/etc. zones, central abundances, and burning regions in one saved
profile. Both check column presence first and only report what the run actually wrote.
"""
from __future__ import annotations

from . import columns
from .plotting import _resolve_profile

# MESA mixing_type enum (the common values) → label.
_MIXING = {1: "convective", 2: "softened_convective", 3: "overshoot",
           4: "semiconvective", 5: "thermohaline", 6: "rotation"}

_CORE_COLS = ["he_core_mass", "c_core_mass", "o_core_mass", "si_core_mass", "fe_core_mass"]
_CENTER_COLS = ["center_h1", "center_he4", "center_c12", "center_n14", "center_o16", "center_ne20"]


def _final(md, col):
    return float(md.data(col)[-1]) if md.in_data(col) else None


def _phase(center: dict) -> str:
    """A coarse evolutionary-phase guess from central abundances."""
    h1 = center.get("center_h1")
    he4 = center.get("center_he4")
    c12 = center.get("center_c12")
    if h1 is not None and h1 > 1e-4:
        return "core hydrogen burning (main sequence)"
    if he4 is not None and he4 > 1e-4:
        return "core helium burning (post main sequence)" if (h1 is not None and h1 <= 1e-4) else "helium burning"
    if c12 is not None and c12 > 1e-4:
        return "advanced burning (carbon and beyond)"
    return "late / unknown phase (central H and He depleted)"


def analyze_history(env: dict, workspace: str) -> dict:
    import numpy as np
    import os
    ws = os.path.abspath(os.path.expanduser(workspace))
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    try:
        md = columns.load_mesa_data(ws, file_type="history")
    except RuntimeError as e:
        return {"error": str(e)}

    center = {c: _final(md, c) for c in _CENTER_COLS if md.in_data(c)}
    cores = {c: _final(md, c) for c in _CORE_COLS if md.in_data(c)}
    summary = {c: _final(md, c) for c in
               ("model_number", "star_age", "star_mass", "log_L", "log_Teff", "log_R",
                "log_center_T", "log_center_Rho", "num_zones") if md.in_data(c)}

    # Key transition: TAMS = first model where center_h1 drops below 1e-6.
    transitions = {}
    if md.in_data("center_h1") and md.in_data("model_number"):
        h1 = md.data("center_h1")
        below = np.where(h1 < 1e-6)[0]
        if below.size:
            mn = md.data("model_number")
            transitions["TAMS_model"] = int(mn[below[0]])
            if md.in_data("star_age"):
                transitions["TAMS_age_yr"] = float(md.data("star_age")[below[0]])

    mixing = {c: _final(md, c) for c in
              ("mass_conv_core", "conv_mx1_top", "conv_mx1_bot") if md.in_data(c)}

    return {
        "workspace": ws,
        "final": summary,
        "central_abundances": center,
        "core_masses": cores,
        "current_mixing": mixing,
        "evolutionary_phase": _phase(center),
        "transitions": transitions,
        "total_models": int(len(md.data("model_number"))) if md.in_data("model_number") else None,
    }


def _zones(mass, mixing_type) -> list:
    """Group contiguous zones by mixing type into mass-coordinate intervals."""
    import numpy as np
    out = []
    n = len(mixing_type)
    i = 0
    while i < n:
        mt = int(mixing_type[i])
        if mt in _MIXING:
            j = i
            while j + 1 < n and int(mixing_type[j + 1]) == mt:
                j += 1
            lo, hi = float(min(mass[i], mass[j])), float(max(mass[i], mass[j]))
            out.append({"type": _MIXING[mt], "bottom_mass": lo, "top_mass": hi,
                        "extent_Msun": round(hi - lo, 6), "cells": int(j - i + 1)})
            i = j + 1
        else:
            i += 1
    return out


def analyze_profile(env: dict, workspace: str, profile_number: int = 0) -> dict:
    import numpy as np
    import os
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
    if not md.in_data("mass"):
        return {"error": "Profile has no 'mass' column; cannot locate zones."}

    mass = md.data("mass")
    ci = int(np.argmin(mass))  # center = smallest mass coordinate
    center = {iso: float(md.data(iso)[ci]) for iso in
              ("h1", "he3", "he4", "c12", "n14", "o16", "ne20", "si28")
              if md.in_data(iso)}

    zones = _zones(mass, md.data("mixing_type")) if md.in_data("mixing_type") else []

    # He-core mass estimate: outermost mass coordinate where H is depleted (X_H1 < 0.01).
    cores = {}
    if md.in_data("h1"):
        depleted = mass[md.data("h1") < 0.01]
        cores["he_core_mass_est"] = float(depleted.max()) if depleted.size else 0.0
    if md.in_data("he4"):
        co = mass[md.data("he4") < 0.01]
        cores["co_core_mass_est"] = float(co.max()) if co.size else 0.0

    # Active burning regions: contiguous mass intervals with eps_nuc above threshold.
    burning = []
    epscol = next((c for c in ("eps_nuc", "log_eps_nuc") if md.in_data(c)), None)
    if epscol:
        eps = md.data(epscol)
        active = (eps > 1.0) if epscol == "eps_nuc" else (eps > 0.0)
        n = len(eps)
        i = 0
        while i < n:
            if active[i]:
                j = i
                while j + 1 < n and active[j + 1]:
                    j += 1
                burning.append({"bottom_mass": float(min(mass[i], mass[j])),
                                "top_mass": float(max(mass[i], mass[j]))})
                i = j + 1
            else:
                i += 1

    return {
        "workspace": ws,
        "profile": os.path.basename(pf),
        "n_zones": int(len(mass)),
        "total_mass_Msun": float(mass.max()),
        "central_abundances": center,
        "mixing_regions": zones,
        "core_masses": cores,
        "burning_regions": burning,
    }
