"""Read-only access to MESA's bundled data libraries under ``$MESA_DIR/data``.

A small, bounded surface: ``list_libraries`` enumerates the ``*_data`` subdirs with curated
descriptions, and ``load_data`` dispatches to internal parsers for the high-value, human-readable
ones — nuclear networks (``.net``), solar-abundance patterns (Lodders), and the isotope table —
falling back to a plain file listing for the rest. Heavy binary tables (EOS/opacity) are listed,
not parsed. Nuclear *rates* have their own tool (mesa_data_rate).
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
    "colors_data": "Filter transmission sets (by survey) + stellar-model SED grids for synthetic photometry.",
    "eosDT_data": "Equation-of-state tables on a (density, temperature) grid.",
    "eosCMS_data": "Chabrier-Mazevet-Soubiran EOS tables.",
    "eosFreeEOS_data": "FreeEOS equation-of-state tables.",
    "eosPC_support_data": "Potekhin-Chabrier EOS support tables.",
    "ionization_data": "Ionization-state tables.",
    "kap_data": "Radiative + conductive opacity tables.",
    "net_data": "Nuclear reaction networks (.net): which isotopes + reactions each network includes.",
    "rates_data": "Reaction-rate data (JINA REACLIB, weak rates) — query via mesa_data_rate.",
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
            "loadable": ["net", "solar", "isotope", "colors"],
            "note": "Use mesa_data_library(library, name) — 'net' (networks), 'solar' (abundances), "
                    "'isotope' (one isotope's properties), 'colors' (filters/models) have dedicated "
                    "parsers; any other data subdir returns a structured inventory."}


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
                "note": "Call mesa_data_library('net', '<network>') to list its isotopes + reactions."}
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
        return {"error": "Pass an isotope name, e.g. mesa_data_library('isotope', 'c12')."}
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


def _human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f}{unit}" if unit == "B" else f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


def _family(fn: str) -> str:
    """Group key for a data file: its name minus a trailing numeric/version run and extension."""
    stem = os.path.splitext(fn)[0]
    return re.sub(r"[_-]?\d[\d._-]*$", "", stem) or stem


def _inventory(sub: str) -> dict:
    """A structured inventory of a data subdir: subdirs, by-extension and by-family file groups."""
    subdirs, files, total = [], [], 0
    for entry in sorted(os.listdir(sub)):
        full = os.path.join(sub, entry)
        if os.path.isdir(full):
            subdirs.append(entry)
        elif os.path.isfile(full):
            files.append(entry)
            try:
                total += os.path.getsize(full)
            except OSError:
                pass
    by_ext: dict = {}
    by_family: dict = {}
    for fn in files:
        by_ext[os.path.splitext(fn)[1] or "(none)"] = by_ext.get(os.path.splitext(fn)[1] or "(none)", 0) + 1
        by_family[_family(fn)] = by_family.get(_family(fn), 0) + 1
    families = sorted(by_family.items(), key=lambda kv: kv[1], reverse=True)[:25]
    return {
        "library": os.path.basename(sub),
        "description": _LIBRARIES.get(os.path.basename(sub), ""),
        "subdirs": subdirs,
        "n_files": len(files),
        "total_size": _human_size(total),
        "by_extension": by_ext,
        "table_families": [{"family": f, "count": c} for f, c in families],
        "sample_files": files[:15],
        "note": "Structured inventory (no numeric parser for this library — EOS/opacity/atm tables "
                "are large binary-ish grids). Use mesa_docs_page for the module's docs.",
    }


def _load_colors(data_dir: str, name: str) -> dict:
    """Inventory the colors library: filter sets (survey → bands) and stellar-model grids."""
    cd = os.path.join(data_dir, "colors_data")
    if not os.path.isdir(cd):
        return {"error": "colors_data not found."}
    filters_dir = os.path.join(cd, "filters")
    models_dir = os.path.join(cd, "stellar_models")
    key = name.strip().lower()

    if key in ("", "summary", "filters"):
        surveys = {}
        if os.path.isdir(filters_dir):
            for survey in sorted(os.listdir(filters_dir)):
                sp = os.path.join(filters_dir, survey)
                if not os.path.isdir(sp):
                    continue
                bands = sorted(os.path.splitext(f)[0]
                               for _r, _d, fs in os.walk(sp) for f in fs if f.endswith(".dat"))
                surveys[survey] = bands
        if key == "filters":
            return {"library": "colors", "filters": surveys,
                    "n_surveys": len(surveys), "n_bands": sum(len(b) for b in surveys.values())}
        models = sorted(os.listdir(models_dir)) if os.path.isdir(models_dir) else []
        return {"library": "colors",
                "filter_surveys": {s: len(b) for s, b in surveys.items()},
                "stellar_models": models,
                "note": "mesa_data_library('colors','filters') lists every band; "
                        "('colors','models') lists the stellar-model grids."}

    if key in ("models", "stellar_models"):
        models = sorted(os.listdir(models_dir)) if os.path.isdir(models_dir) else []
        return {"library": "colors", "stellar_models": models, "count": len(models)}
    return {"error": f"colors: unknown selector '{name}'. Use '', 'filters', or 'models'."}


def load_data(env: dict, library: str, name: str = "") -> dict:
    """Dispatch to a parser for a known library, else return a structured inventory of the subdir."""
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
    if key in ("colors", "color"):
        return _load_colors(data_dir, name)

    # Fallback: a structured inventory of the named data subdir.
    sub = os.path.join(data_dir, library if library.endswith("_data") else library + "_data")
    if os.path.isdir(sub):
        return _inventory(sub)
    return {"error": f"Unknown library '{library}'. Use mesa_data_library to discover them."}
