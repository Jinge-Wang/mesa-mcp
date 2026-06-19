"""Query MESA's nuclear reaction-rate data (JINA REACLIB) and evaluate it at a temperature.

Read-only against ``$MESA_DIR/data/rates_data``. Resolves a MESA reaction handle (e.g.
``r_c12_c12_to_he4_ne20``) to its reactant/product isotopes via ``reactions.list``, finds the
matching REACLIB fit set(s), and returns each set's 7 fit coefficients, its source ("set label"),
and the rate evaluated at a given temperature with the standard REACLIB formula:

    NA<σv> = exp( a0 + a1/T9 + a2/T9^(1/3) + a3·T9^(1/3) + a4·T9 + a5·T9^(5/3) + a6·ln(T9) )

(T9 = temperature in 10^9 K). Multiple sets for the same reaction (e.g. resonant + non-resonant)
are summed for the total. Pure standard library — no numpy needed for scalar evaluation.
"""
from __future__ import annotations

import glob
import math
import os
import re

from . import config, inlist

# REACLIB "set label" → human-readable source. The label's trailing flag (n non-resonant,
# r resonant, w/s weak, v reverse-derived) is informational; the stem is the data source.
_LABEL_SOURCES = {
    "cf88": "Caughlan & Fowler 1988",
    "ka02": "Kunz et al. 2002",
    "nacr": "NACRE (Angulo et al. 1999)",
    "an06": "Angulo / NACRE",
    "il10": "Iliadis et al. 2010",
    "rath": "Rauscher & Thielemann 2000 (Hauser-Feshbach)",
    "ths8": "Rauscher & Thielemann 2000 (THIELEMANN)",
    "wc12": "Wallace & Caughlan / weak",
    "wc17": "weak (REACLIB)",
    "wc07": "weak (REACLIB)",
    "wfh": "Fuller, Fowler & Newman (weak)",
    "fkth": "Fuller-Kar / Thielemann",
    "wies": "Wiescher",
    "wag": "Wagoner",
    "laur": "Laury",
    "bb92": "Bao et al. 1992",
    "ec": "electron capture",
    "bet+": "beta-plus decay",
    "bet-": "beta-minus decay",
}

# REACLIB chapter → (n_reactants, n_products).
_CHAPTERS = {
    1: (1, 1), 2: (1, 2), 3: (1, 3), 4: (2, 1), 5: (2, 2), 6: (2, 3),
    7: (2, 4), 8: (3, 1), 9: (3, 2), 10: (4, 2), 11: (1, 4),
}

_COUNT_ISO = re.compile(r"(\d+)\s+([a-zA-Z]+\d*)")

# REACLIB spells the light particles p/n/d/t/a; MESA handles use h1/neut/h2/h3/he4. Canonicalize
# both sides before matching so a handle's isotopes line up with the REACLIB entry.
_ISO_CANON = {"p": "h1", "n": "neut", "d": "h2", "t": "h3", "a": "he4"}

_MEMO: dict = {}


def _canon(iso: str) -> str:
    return _ISO_CANON.get(iso.lower(), iso.lower())


def _rates_dir(mesa_dir: str) -> "str | None":
    d = os.path.join(mesa_dir, "data", "rates_data") if mesa_dir else None
    return d if d and os.path.isdir(d) else None


def reaclib_file(mesa_dir: str) -> "str | None":
    """Pick the JINA REACLIB file MESA uses by default (the ``*_default`` set)."""
    d = _rates_dir(mesa_dir)
    if not d:
        return None
    cands = sorted(glob.glob(os.path.join(d, "jina_reaclib_results*")))
    if not cands:
        return None
    for key in ("20171020_default", "_default", "default"):
        for c in cands:
            if key in os.path.basename(c):
                return c
    return cands[-1]


def reaclib_rate(coeffs: list, t9: float) -> float:
    """Evaluate the 7-term REACLIB fit at temperature ``t9`` (10^9 K)."""
    a0, a1, a2, a3, a4, a5, a6 = coeffs
    return math.exp(a0 + a1 / t9 + a2 / t9 ** (1 / 3) + a3 * t9 ** (1 / 3)
                    + a4 * t9 + a5 * t9 ** (5 / 3) + a6 * math.log(t9))


def label_source(label: str) -> str:
    stem = label.strip().rstrip("nrwsv")
    for k in sorted(_LABEL_SOURCES, key=len, reverse=True):
        if stem.startswith(k) or label.strip().startswith(k):
            return _LABEL_SOURCES[k]
    return "JINA REACLIB set"


def _parse_floats_13(line: str, n: int) -> list:
    """Parse ``n`` fixed-width-13 floats from a REACLIB coefficient line."""
    out = []
    for i in range(n):
        field = line[i * 13:(i + 1) * 13].strip()
        out.append(float(field) if field else 0.0)
    return out


def _iso_key(reactants: list, products: list) -> tuple:
    return (tuple(sorted(_canon(x) for x in reactants)),
            tuple(sorted(_canon(x) for x in products)))


def _build_reaclib_index(path: str) -> dict:
    """Parse a REACLIB file into {(reactants, products): [entry, ...]} (memoized by mtime)."""
    st = os.stat(path)
    sig = (st.st_size, round(st.st_mtime, 3))
    memo = _MEMO.get(path)
    if memo and memo[0] == sig:
        return memo[1]

    index: dict = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    i, n = 0, len(lines)
    while i + 3 < n:
        head = lines[i].strip()
        if not (head.isdigit() and int(head) in _CHAPTERS):
            i += 1
            continue
        chapter = int(head)
        nr, npd = _CHAPTERS[chapter]
        hdr, c1, c2 = lines[i + 1], lines[i + 2], lines[i + 3]
        nuclei = [hdr[5 + 5 * k:10 + 5 * k].strip() for k in range(6)]
        nuclei = [x for x in nuclei if x]
        if len(nuclei) != nr + npd:
            i += 1
            continue
        reactants, products = nuclei[:nr], nuclei[nr:]
        rest = hdr[35:].split()
        label = rest[0] if rest else ""
        try:
            q = float(rest[-1]) if rest else 0.0
        except ValueError:
            q = 0.0
        try:
            coeffs = _parse_floats_13(c1, 4) + _parse_floats_13(c2, 3)
        except ValueError:
            i += 4
            continue
        index.setdefault(_iso_key(reactants, products), []).append({
            "label": label, "chapter": chapter, "q": q,
            "reactants": reactants, "products": products, "coeffs": coeffs,
        })
        i += 4

    _MEMO[path] = (sig, index)
    return index


def _reactions_list(mesa_dir: str) -> "list[dict]":
    """Parse reactions.list (fixed columns) into [{handle, reactants, products, q}] (memoized)."""
    d = _rates_dir(mesa_dir)
    path = os.path.join(d, "reactions.list") if d else None
    if not path or not os.path.isfile(path):
        return []
    st = os.stat(path)
    sig = (st.st_size, round(st.st_mtime, 3))
    memo = _MEMO.get(path)
    if memo and memo[0] == sig:
        return memo[1]

    rows = []
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for ln in f:
            if not ln.strip() or ln.lstrip().startswith("!"):
                continue
            handle = ln[0:35].strip()
            if not handle or "=>" not in ln:
                continue
            reactants = _expand(ln[35:70])
            products = _expand(ln[73:108])
            if not reactants or not products:
                continue
            qtxt = ln[109:127].strip()
            try:
                q = float(qtxt.replace("d", "e").replace("D", "e")) if qtxt else None
            except ValueError:
                q = None
            rows.append({"handle": handle, "reactants": reactants,
                         "products": products, "q": q})
    _MEMO[path] = (sig, rows)
    return rows


def _expand(segment: str) -> list:
    """Expand a 'count iso' segment (e.g. '2 c12') into a flat isotope list ([c12, c12])."""
    out = []
    for cnt, iso in _COUNT_ISO.findall(segment):
        out.extend([iso.lower()] * int(cnt))
    return out


_IDX_RE = re.compile(r"\((\d+)\)")


def _controls_inlist(path: str) -> "str | None":
    """Resolve the inlist file holding the &controls namelist (accepts a file or a workspace)."""
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for f in sorted(glob.glob(os.path.join(path, "inlist*"))):
            if f.endswith(".bak"):
                continue
            try:
                lines = open(f, "r", encoding="utf-8", errors="replace").read().splitlines()
            except OSError:
                continue
            if inlist._find_namelist(lines, "controls"):
                return f
    return None


def _fortran_double(factor: float) -> str:
    """Render a multiplier as a Fortran double literal (e.g. 0.5 → '0.5d0')."""
    s = repr(float(factor))
    return s if ("e" in s or "E" in s) else f"{s}d0"


def set_rate_factor(env: dict, path: str, reaction: str, factor: float) -> dict:
    """Scale a specific reaction's rate via MESA's special_rate_factor array.

    Patches (into &controls) `reaction_for_special_factor(i)`, `special_rate_factor(i)`, and
    `num_special_rate_factors`, reusing the slot if the reaction is already scaled and otherwise
    appending the next index. A thin wrapper over inlist.set_option — no rate file is read.
    """
    target = _controls_inlist(path)
    if not target:
        return {"error": f"No inlist with a &controls namelist found at {path}."}

    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    handle = reaction.strip()
    rows = _reactions_list(mesa_dir)
    if rows and not any(r["handle"] == handle for r in rows):
        near = [r["handle"] for r in rows if handle.lower() in r["handle"].lower()][:15]
        return {"error": f"Reaction handle '{handle}' not found in reactions.list.",
                "suggestions": near}

    # Find existing slots, reusing this reaction's index if already present.
    used, existing_idx = {}, None
    for s in inlist.read_settings(target):
        m = _IDX_RE.search(s["name"])
        if not m:
            continue
        idx = int(m.group(1))
        if s["name"].startswith("reaction_for_special_factor"):
            used[idx] = s["value"].strip().strip("'\"")
            if used[idx] == handle:
                existing_idx = idx
    i = existing_idx or (max(used) + 1 if used else 1)
    num = max([i] + list(used))

    patches = []
    for name, value in (
        (f"reaction_for_special_factor({i})", f"'{handle}'"),
        (f"special_rate_factor({i})", _fortran_double(factor)),
        ("num_special_rate_factors", str(num)),
    ):
        res = inlist.set_option(env, target, name, value, namelist="controls")
        if res.get("error"):
            return {"error": f"Failed to set {name}: {res['error']}", "patched": patches}
        patches.append({"name": name, "value": value, "action": res["action"]})

    return {"inlist": target, "reaction": handle, "factor": factor, "index": i,
            "num_special_rate_factors": num, "reused_slot": existing_idx is not None,
            "patches": patches}


def get_reaction_rate(env: dict, reaction: str, t9: float = 0.5) -> dict:
    """Resolve ``reaction`` and return its REACLIB fit set(s) evaluated at ``t9``."""
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if not _rates_dir(mesa_dir):
        return {"error": f"No data/rates_data under MESA_DIR ({mesa_dir or 'unset'})."}
    if t9 <= 0:
        return {"error": "t9 (temperature in 10^9 K) must be positive."}

    handle = reaction.strip()
    rows = _reactions_list(mesa_dir)
    match = next((r for r in rows if r["handle"] == handle), None)
    if not match:
        near = [r["handle"] for r in rows if handle.lower() in r["handle"].lower()][:15]
        return {"error": f"Reaction handle '{handle}' not found in reactions.list.",
                "suggestions": near}

    rf = reaclib_file(mesa_dir)
    if not rf:
        return {"error": "No jina_reaclib_results* file found in data/rates_data."}
    index = _build_reaclib_index(rf)
    key = _iso_key(match["reactants"], match["products"])
    entries = index.get(key, [])

    sets, total = [], 0.0
    for e in entries:
        rate = reaclib_rate(e["coeffs"], t9)
        total += rate
        sets.append({
            "label": e["label"],
            "source": label_source(e["label"]),
            "q_MeV": e["q"],
            "coeffs": e["coeffs"],
            "rate": rate,
        })

    q_top = match["q"] if match["q"] is not None else (sets[0]["q_MeV"] if sets else None)
    return {
        "reaction": handle,
        "reactants": match["reactants"],
        "products": match["products"],
        "q_MeV": q_top,
        "t9": t9,
        "temperature_K": t9 * 1e9,
        "reaclib_file": os.path.basename(rf),
        "n_sets": len(sets),
        "sets": sets,
        "total_rate": total,
        "rate_units": ("1/s (1 reactant) or cm^3 mol^-1 s^-1 (2 reactants) or "
                       "cm^6 mol^-2 s^-1 (3 reactants) — i.e. NA<σv> per reaction"),
        "note": (None if sets else
                 "No REACLIB set matched these isotopes; it may be a weak/tabulated rate "
                 "(see weak_info.list / weakreactions.tables) rather than a REACLIB fit."),
    }
