"""Read-only access to MESA's bundled data libraries under ``$MESA_DIR/data``.

A small, bounded surface: ``list_libraries`` enumerates the ``*_data`` subdirs with curated
descriptions, and ``load_data`` dispatches to internal parsers for the high-value, human-readable
ones — nuclear networks (``.net``), solar-abundance patterns (Lodders), and the isotope table —
falling back to a plain file listing for the rest. Heavy binary tables (EOS/opacity) are listed,
not parsed. Nuclear *rates* have their own tool (mesa_get_reaction_rate).
"""
from __future__ import annotations

import glob
import os
import re

from . import config

# Curated descriptions for the data/ subdirectories.
_LIBRARIES = {
    "atm_data": "Atmosphere boundary-condition tables (T-tau relations, model atmospheres).",
    "chem_data": "Chemical/isotope data: isotopes.data (masses, Z, N) + solar abundance patterns (Lodders).",
    "colors_data": "Bolometric corrections / color-magnitude tables.",
    "eosDT_data": "Equation-of-state tables on a (density, temperature) grid.",
    "eosCMS_data": "Chabrier-Mazevet-Soubiran EOS tables.",
    "eosFreeEOS_data": "FreeEOS equation-of-state tables.",
    "eosPC_support_data": "Potekhin-Chabrier EOS support tables.",
    "ionization_data": "Ionization-state tables.",
    "kap_data": "Radiative + conductive opacity tables.",
    "net_data": "Nuclear reaction networks (.net): which isotopes + reactions each network includes.",
    "rates_data": "Reaction-rate data (JINA REACLIB, weak rates) — query via mesa_get_reaction_rate.",
    "roche_data": "Roche-lobe geometry tables (binary).",
    "star_data": "Miscellaneous star-module support data.",
}

_TOKEN = re.compile(r"[A-Za-z_]\w*")
_INCLUDE = re.compile(r"include\s+['\"]([^'\"]+)['\"]")


def _data_dir(mesa_dir: str) -> "str | None":
    d = os.path.join(mesa_dir, "data") if mesa_dir else None
    return d if d and os.path.isdir(d) else None


def _nets_dir(data_dir: str) -> str:
    return os.path.join(data_dir, "net_data", "nets")


def list_libraries(env: dict) -> dict:
    """Enumerate the data/ libraries with descriptions and file counts."""
    data_dir = _data_dir(env.get(config.MESA_DIR_ENV, ""))
    if not data_dir:
        return {"error": "No data/ directory under MESA_DIR."}
    libs = []
    for name in sorted(os.listdir(data_dir)):
        full = os.path.join(data_dir, name)
        if not os.path.isdir(full):
            continue
        try:
            n_files = sum(len(fs) for _r, _d, fs in os.walk(full))
        except OSError:
            n_files = None
        libs.append({"library": name, "description": _LIBRARIES.get(name, ""),
                     "files": n_files})
    return {"data_dir": data_dir, "libraries": libs,
            "loadable": ["net", "solar", "isotope"],
            "note": "Use mesa_load_data(library, name) — 'net' (networks), 'solar' (abundances), "
                    "'isotope' (one isotope's properties) have parsers; others list files."}


def _strip_comment(line: str) -> str:
    return line.split("!", 1)[0]


def _parse_net(nets_dir: str, name: str, _seen: "set | None" = None) -> dict:
    """Parse a .net network into its isotopes, reactions, and resolved includes (recursive)."""
    seen = _seen if _seen is not None else set()
    base = name[:-4] if name.endswith(".net") else name
    if base in seen:
        return {"isotopes": [], "reactions": [], "includes": []}
    seen.add(base)
    path = os.path.join(nets_dir, base + ".net")
    if not os.path.isfile(path):
        path = os.path.join(nets_dir, base)  # include files have no extension
    if not os.path.isfile(path):
        return {"error": f"Network '{name}' not found in {nets_dir}."}

    isotopes, reactions, includes = [], [], []
    mode = None  # 'isos' | 'reactions'
    for raw in open(path, "r", encoding="utf-8", errors="replace"):
        line = _strip_comment(raw)
        inc = _INCLUDE.search(line)
        if inc:
            includes.append(inc.group(1))
            continue
        if "add_isos" in line:
            mode = "isos"
        elif "add_reactions" in line or "add_basic_reactions" in line:
            mode = "reactions"
        if mode and "(" in line:
            line = line.split("(", 1)[1]
        toks = [t for t in _TOKEN.findall(line)
                if t not in ("add_isos", "add_reactions", "add_basic_reactions", "include")]
        if mode == "isos":
            isotopes.extend(toks)
        elif mode == "reactions":
            reactions.extend(toks)
        if ")" in _strip_comment(raw):
            mode = None

    merged_isos, merged_rx = list(isotopes), list(reactions)
    for inc in includes:
        sub = _parse_net(nets_dir, inc, seen)
        merged_isos = sub.get("isotopes", []) + merged_isos
        merged_rx = sub.get("reactions", []) + merged_rx
    # de-dup, preserve order
    merged_isos = list(dict.fromkeys(merged_isos))
    merged_rx = list(dict.fromkeys(merged_rx))
    return {"isotopes": merged_isos, "reactions": merged_rx, "includes": includes}


def _builtin_macro(nets_dir: str, base: str) -> "str | None":
    """Return the macro call (e.g. 'approx21(cr56)') from a built-in net's .net file, if any."""
    path = os.path.join(nets_dir, base + ".net")
    if not os.path.isfile(path):
        return None
    for raw in open(path, "r", encoding="utf-8", errors="replace"):
        line = _strip_comment(raw).strip()
        if line:
            return line
    return None


def _load_net(data_dir: str, name: str) -> dict:
    nets = _nets_dir(data_dir)
    if not os.path.isdir(nets):
        return {"error": "No net_data/nets directory found."}
    if not name:
        files = sorted(os.path.basename(f)[:-4]
                       for f in glob.glob(os.path.join(nets, "*.net")))
        return {"library": "net", "available_networks": files, "count": len(files),
                "note": "Call mesa_load_data('net', '<network>') to list its isotopes + reactions."}
    parsed = _parse_net(nets, name)
    if parsed.get("error"):
        return parsed
    base = name[:-4] if name.endswith(".net") else name
    out = {"library": "net", "network": base,
           "n_isotopes": len(parsed["isotopes"]), "isotopes": parsed["isotopes"],
           "n_reactions": len(parsed["reactions"]), "reactions": parsed["reactions"],
           "includes": parsed["includes"]}
    if not (parsed["isotopes"] or parsed["reactions"] or parsed["includes"]):
        # e.g. approx21.net is just `approx21(cr56)` — a built-in net hard-coded in MESA's net
        # module source, not declared via add_isos.
        macro = _builtin_macro(nets, base)
        out["note"] = (f"'{base}' is a built-in network (`{macro}`) defined in MESA's net module "
                       "source (net/private), not via add_isos — its isotope list isn't in the "
                       ".net file." if macro else
                       "No isotopes/reactions declared in this .net file.")
        out["builtin"] = macro
    return out


def _load_solar(data_dir: str, name: str) -> dict:
    pattern = name or "lodders09"
    path = os.path.join(data_dir, "chem_data", pattern + ".data")
    if not os.path.isfile(path):
        avail = sorted(os.path.basename(f)[:-5]
                       for f in glob.glob(os.path.join(data_dir, "chem_data", "lodders*.data")))
        return {"error": f"Abundance pattern '{pattern}' not found.", "available": avail}
    rows = []
    for ln in open(path, "r", encoding="utf-8", errors="replace"):
        parts = ln.split()
        if len(parts) != 4:
            continue
        z, elem, a, frac = parts
        try:
            rows.append({"Z": int(z), "element": elem, "A": int(a),
                         "mass_fraction": float(frac)})
        except ValueError:
            continue
    return {"library": "solar", "pattern": pattern, "n_isotopes": len(rows),
            "total_mass_fraction": round(sum(r["mass_fraction"] for r in rows), 6),
            "isotopes": rows}


def _load_isotope(data_dir: str, name: str) -> dict:
    path = os.path.join(data_dir, "chem_data", "isotopes.data")
    if not os.path.isfile(path):
        return {"error": "chem_data/isotopes.data not found."}
    if not name:
        return {"error": "Pass an isotope name, e.g. mesa_load_data('isotope', 'c12')."}
    target = name.strip().lower()
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.read().splitlines()
    for ln in lines:
        parts = ln.split()
        if len(parts) >= 6 and parts[0].lower() == target:
            try:
                return {"library": "isotope", "isotope": parts[0],
                        "mass_amu": float(parts[1]), "Z": int(parts[2]), "N": int(parts[3]),
                        "spin": float(parts[4]), "mass_excess_MeV": float(parts[5])}
            except ValueError:
                break
    return {"error": f"Isotope '{name}' not found in isotopes.data."}


def load_data(env: dict, library: str, name: str = "") -> dict:
    """Dispatch to a parser for a known library, else list the matching data subdir's files."""
    data_dir = _data_dir(env.get(config.MESA_DIR_ENV, ""))
    if not data_dir:
        return {"error": "No data/ directory under MESA_DIR."}
    key = library.strip().lower().replace("_data", "")
    if key in ("net", "network", "networks"):
        return _load_net(data_dir, name.strip())
    if key in ("solar", "abundance", "abundances"):
        return _load_solar(data_dir, name.strip())
    if key in ("isotope", "isotopes", "chem"):
        return _load_isotope(data_dir, name.strip())

    # Fallback: if it names a real data subdir, list its files (bounded).
    sub = os.path.join(data_dir, library if library.endswith("_data") else library + "_data")
    if os.path.isdir(sub):
        files = sorted(os.listdir(sub))[:200]
        return {"library": os.path.basename(sub), "description": _LIBRARIES.get(os.path.basename(sub), ""),
                "files": files, "count": len(files),
                "note": "No dedicated parser for this library yet — listing contents."}
    return {"error": f"Unknown library '{library}'. Use mesa_list_data_libraries to discover them."}
