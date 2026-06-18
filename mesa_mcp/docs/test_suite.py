"""Index the MESA test suite and extract per-case descriptions and real inlists.

Local-first: enumerate the actual case directories under
``$MESA_DIR/<module>/test_suite`` (ground truth), and read descriptions from
``docs/source/test_suite/<name>.rst`` or the case ``README``. The network fallback
parses ``test_suite.html`` / ``test_suite/<name>.html`` (description only — the real
inlist files exist only in a local install).
"""
from __future__ import annotations

import glob
import os

from .. import config, version
from . import fetch, sources

_MODULES = ("star", "binary", "astero")


def _module_ts_dir(mesa_dir: str, module: str) -> str:
    return os.path.join(mesa_dir, module, "test_suite")


def _is_case(d: str) -> bool:
    """A directory is a test case if it has an ``rn`` script or any ``inlist*`` file."""
    return os.path.isdir(d) and (
        os.path.exists(os.path.join(d, "rn")) or bool(glob.glob(os.path.join(d, "inlist*")))
    )


def _list_cases(ts_dir: str) -> list:
    if not os.path.isdir(ts_dir):
        return []
    return sorted(n for n in os.listdir(ts_dir) if _is_case(os.path.join(ts_dir, n)))


def _read(path: str, limit: int | None = None) -> "str | None":
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            data = f.read()
    except OSError:
        return None
    return data[:limit] if limit else data


def index(env: dict) -> dict:
    """Return the test-suite index: per-module case names + counts. Local-first."""
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if mesa_dir and os.path.isdir(mesa_dir):
        modules = {}
        for m in _MODULES:
            cases = _list_cases(_module_ts_dir(mesa_dir, m))
            if cases:
                modules[m] = cases
        return {
            "source": "local",
            "docs_version": version.docs_version(env),
            "counts": {m: len(c) for m, c in modules.items()},
            "modules": modules,
            "hint": "Use mesa_fetch_test_suite_details(name) for a case's description and inlists.",
        }
    return _network_index(env)


def _find_case_dir(mesa_dir: str, test_name: str):
    for m in _MODULES:
        d = os.path.join(_module_ts_dir(mesa_dir, m), test_name)
        if _is_case(d):
            return m, d
    return None, None


def details(env: dict, test_name: str, max_inlists: int = 6, per_inlist_chars: int = 6000) -> dict:
    """Return description + real inlist contents for one case. Local-first."""
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if mesa_dir:
        module, case_dir = _find_case_dir(mesa_dir, test_name)
        if case_dir:
            return _local_details(env, module, case_dir, test_name, max_inlists, per_inlist_chars)
    return _network_details(env, test_name)


def _local_details(env, module, case_dir, test_name, max_inlists, per_inlist_chars) -> dict:
    desc = None
    local_docs = sources.local_docs_dir(env)
    if local_docs:
        raw = _read(os.path.join(local_docs, "test_suite", test_name + ".rst"))
        if raw:
            desc = fetch.rst_to_text(raw)
    if not desc:
        readme = _read(os.path.join(case_dir, "README.rst")) or _read(os.path.join(case_dir, "README"))
        if readme:
            desc = fetch.rst_to_text(readme)

    inlist_files = sorted(os.path.basename(p) for p in glob.glob(os.path.join(case_dir, "inlist*")))
    inlists = {}
    for name in inlist_files[:max_inlists]:
        content = _read(os.path.join(case_dir, name), per_inlist_chars)
        if content is not None:
            inlists[name] = content

    aux = [f for f in ("rn", "rn1", "re", "ck", "history_columns.list", "profile_columns.list",
                       os.path.join("src", "run_star_extras.f90"))
           if os.path.exists(os.path.join(case_dir, f))]

    truncated = any(len(v) >= per_inlist_chars for v in inlists.values()) or len(inlist_files) > max_inlists
    return {
        "source": "local",
        "test_name": test_name,
        "module": module,
        "case_dir": case_dir,
        "description": desc or "(no description found)",
        "inlist_files": inlist_files,
        "inlists": inlists,
        "auxiliary_files": aux,
        "note": ("Some inlists were truncated or omitted; read a full file by path with "
                 "mesa_fetch_doc_page if needed." if truncated else ""),
    }


def _network_index(env: dict) -> dict:
    base = sources.network_base(env)
    try:
        html = fetch.http_get(base + "test_suite.html")
    except RuntimeError as e:
        return {"source": "unavailable", "results": [], "note": str(e)}
    except Exception as e:
        return {"source": "network-error", "results": [], "note": f"{e}"}
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {"source": "unavailable", "results": [], "note": fetch._MISSING_DEPS}

    soup = BeautifulSoup(html, "html.parser")
    names = set()
    for a in soup.select("a.reference.internal[href*='test_suite/']"):
        stem = a.get("href", "").split("test_suite/")[-1].split("#")[0].replace(".html", "")
        if stem:
            names.add(stem)
    return {"source": "network", "docs_version": version.docs_version(env), "cases": sorted(names)}


def _network_details(env: dict, test_name: str) -> dict:
    base = sources.network_base(env)
    url = base + f"test_suite/{test_name}.html"
    try:
        text = fetch.html_to_text(fetch.http_get(url))
    except RuntimeError as e:
        return {"source": "unavailable", "test_name": test_name, "note": str(e)}
    except Exception as e:
        return {"source": "network-error", "test_name": test_name, "note": f"{e}"}
    return {
        "source": "network",
        "test_name": test_name,
        "url": url,
        "description": text[:4000],
        "note": "Network details: real inlist files are only available from a local MESA install.",
    }
