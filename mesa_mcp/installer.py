"""Help a user install MESA: detect platform, find the latest release + matching SDK, and
(with permission) add a ``load_mesa`` shell function instead of fragile global exports.

The latest MESA release *and* the platform SDKs are published in the MESA Zenodo community
(``type=software``), so both download links come from one REST query — no HTML scraping. The
Townsend SDK page is kept only as a human reference. Actually downloading (~2 GB) and building is
left to the user (or to ``mesa_execute_shell`` with explicit consent); these tools provide the plan
and write the shell helper.
"""
from __future__ import annotations

import os
import platform
import re

from . import config, environment

MESASDK_PAGE = "http://user.astro.wisc.edu/~townsend/static.php?ref=mesasdk"
INSTALL_DOCS = "https://docs.mesastar.org/en/latest/installation.html"
_ZENODO_API = "https://zenodo.org/api/records"
_RELEASE_VER = re.compile(r"^r?\d+\.\d+(\.\d+)?$")

# Concept-DOI record IDs for the SDKs (all-versions DOIs that always resolve to the latest
# release). Fetching api/records/<conceptrecid> returns the newest version's files directly —
# more robust than a community search, which can rate-limit or reorder.
_SDK_CONCEPT = {
    "mac_arm": "13768950",   # https://doi.org/10.5281/zenodo.13768950
    "linux": "2603136",      # https://doi.org/10.5281/zenodo.2603136
    "mac_intel": "2603175",  # https://doi.org/10.5281/zenodo.2603175
}
_SDK_DOI_URL = {k: f"https://doi.org/10.5281/zenodo.{v}" for k, v in _SDK_CONCEPT.items()}


def detect_platform() -> dict:
    """Detect OS/arch and the SDK variant this machine needs."""
    system = platform.system()
    machine = platform.machine().lower()
    if system == "Darwin":
        sdk_key = "mac_arm" if machine in ("arm64", "aarch64") else "mac_intel"
        label = "macOS (Apple Silicon/ARM)" if sdk_key == "mac_arm" else "macOS (Intel)"
    elif system == "Linux":
        sdk_key = "linux"
        label = "Linux (x86-64)" if machine in ("x86_64", "amd64") else f"Linux ({machine})"
    else:
        sdk_key, label = None, f"{system}/{machine} (unsupported by the MESA SDK)"
    return {"system": system, "machine": machine, "sdk_key": sdk_key, "platform_label": label}


def _classify(title: str, version: str, file_key: str) -> "str | None":
    t = title.lower()
    if "mesa sdk" in t and "linux" in t:
        return "sdk_linux"
    if "mesa sdk" in t and "arm" in t:
        return "sdk_mac_arm"
    if "mesa sdk" in t and "mac" in t:
        return "sdk_mac_intel"
    if t.startswith("modules for experiments"):
        fk = file_key.lower()
        if _RELEASE_VER.match(version or "") and not any(
                s in fk for s in ("rc", "prerelease", "summerschool")):
            return "release"
    return None


def _record_info(rec: dict) -> "dict | None":
    """Extract {version, title, html_url, file, size_mb, download_url} from a Zenodo record/hit."""
    m = rec.get("metadata", {})
    files = rec.get("files") or []
    if not files:
        return None
    f0 = files[0]
    return {
        "version": m.get("version"),
        "title": m.get("title"),
        "html_url": rec.get("links", {}).get("self_html"),
        "file": f0.get("key"),
        "size_mb": round(f0.get("size", 0) / 1e6) if f0.get("size") else None,
        "download_url": (f0.get("links") or {}).get("self"),
    }


def fetch_sdk(sdk_key: str, timeout: int = 20) -> "dict | None":
    """Resolve an SDK's latest download via its concept DOI record (robust). None on failure."""
    recid = _SDK_CONCEPT.get(sdk_key)
    if not recid:
        return None
    try:
        import httpx
        r = httpx.get(f"{_ZENODO_API}/{recid}", timeout=timeout, follow_redirects=True)
        r.raise_for_status()
        info = _record_info(r.json())
    except Exception:
        return None
    if info:
        info["doi"] = _SDK_DOI_URL.get(sdk_key)
    return info


def fetch_mesa_software(timeout: int = 20) -> dict:
    """Query the MESA Zenodo community for the latest release + per-platform SDKs (search-based)."""
    try:
        import httpx
    except ImportError:
        return {"error": "httpx not available to query Zenodo."}
    try:
        r = httpx.get(_ZENODO_API, params={"communities": "mesa", "type": "software",
                                           "sort": "mostrecent", "size": 25}, timeout=timeout)
        r.raise_for_status()
        hits = r.json().get("hits", {}).get("hits", [])
    except Exception as e:
        return {"error": f"Zenodo query failed: {type(e).__name__}: {e}"}

    found: dict = {}
    for h in hits:
        m = h.get("metadata", {})
        f0 = (h.get("files") or [{}])[0]
        kind = _classify(m.get("title", ""), m.get("version", ""), f0.get("key", ""))
        if not kind or kind in found:  # keep the most recent (first) of each
            continue
        found[kind] = _record_info(h)
    if not found:
        return {"error": "No MESA software records found on Zenodo."}
    return {
        "release": found.get("release"),
        "sdks": {"linux": found.get("sdk_linux"),
                 "mac_intel": found.get("sdk_mac_intel"),
                 "mac_arm": found.get("sdk_mac_arm")},
    }


def build_load_mesa(mesa_dir: str, mesasdk_root: str, omp_threads: int = 0) -> str:
    """Return the text of a ``load_mesa`` shell function (sourced from the user's rc)."""
    n = omp_threads or (os.cpu_count() or 2)
    return (
        "load_mesa() {\n"
        f'    export MESA_DIR="{mesa_dir}"\n'
        f'    export MESASDK_ROOT="{mesasdk_root}"\n'
        '    source "$MESASDK_ROOT/bin/mesasdk_init.sh"\n'
        f"    export OMP_NUM_THREADS={n}\n"
        '    export PATH="$MESA_DIR/scripts/shmesa:$PATH"\n'
        '    export PS1="(mesa) $PS1"\n'
        "}\n"
    )


_LOAD_MESA_DEF = re.compile(r"(^|\s)(function\s+)?load_mesa\s*\(\)", re.MULTILINE)


def _rc_defines(rc: str) -> bool:
    try:
        return bool(_LOAD_MESA_DEF.search(open(rc, "r", encoding="utf-8", errors="replace").read()))
    except OSError:
        return False


def detect_load_mesa() -> dict:
    """Report whether a ``load_mesa`` function is already defined in the user's shell rc."""
    for shell in environment._candidate_shells():
        rc = environment._rc_file_for(shell)
        if _rc_defines(rc):
            return {"defined": True, "rc_file": rc}
    return {"defined": False, "rc_file": None}


def write_load_mesa(mesa_dir: str, mesasdk_root: str, confirm: bool = False,
                    shell_rc: str = "", omp_threads: int = 0) -> dict:
    """Append a ``load_mesa`` function to the user's shell rc (confirmation-gated, backed up)."""
    if " " in mesa_dir:
        return {"error": "MESA_DIR path contains spaces — the MESA build system does not support that."}
    rc = os.path.abspath(os.path.expanduser(shell_rc)) if shell_rc else \
        environment._rc_file_for((environment._candidate_shells() or ["/bin/zsh"])[0])

    if _rc_defines(rc):
        return {"error": f"A load_mesa function already exists in {rc}. "
                         "Edit it manually rather than appending a duplicate.",
                "rc_file": rc}
    # Also flag (but don't block) a definition in a different rc.
    elsewhere = detect_load_mesa()
    other_warning = (f"Note: load_mesa is also defined in {elsewhere['rc_file']}."
                     if elsewhere["defined"] and elsewhere["rc_file"] != rc else None)

    snippet = build_load_mesa(mesa_dir, mesasdk_root, omp_threads)
    block = ("\n# >>> MESA load_mesa (added by mesa-mcp) >>>\n"
             "# Run `load_mesa` in a new shell before using MESA.\n"
             f"{snippet}"
             "# <<< MESA load_mesa <<<\n")

    if not confirm:
        return {"applied": False, "dry_run": True, "rc_file": rc, "would_append": block,
                "other_definition": other_warning,
                "note": "Dry run — nothing written. Re-call with confirm=True to append this to your "
                        "shell rc. Then open a new shell (or `source` the rc) and run `load_mesa`."}

    try:
        if os.path.exists(rc):
            import shutil
            shutil.copy2(rc, rc + ".bak")
        with open(rc, "a", encoding="utf-8") as f:
            f.write(block)
    except OSError as e:
        return {"error": f"Could not write {rc}: {e}"}
    return {"applied": True, "rc_file": rc, "backup": rc + ".bak" if os.path.exists(rc + ".bak") else None,
            "other_definition": other_warning,
            "note": "Added. Open a new shell (or source the rc) and run `load_mesa` before MESA work."}


def installation_plan(env: dict, timeout: int = 20) -> dict:
    """Assemble a platform-aware MESA installation plan with download links and the load_mesa step."""
    plat = detect_platform()

    # SDKs: primary = concept DOI (robust); per-key fallback = community search.
    sdks, sources, search = {}, {}, None
    for key in ("linux", "mac_intel", "mac_arm"):
        rec = fetch_sdk(key, timeout)
        if rec:
            sdks[key], sources[key] = rec, "concept_doi"
        else:
            if search is None:
                search = fetch_mesa_software(timeout)
            sdks[key] = (search.get("sdks") or {}).get(key) if isinstance(search, dict) else None
            sources[key] = "zenodo_search"

    # The release comes only from the community search (no dedicated concept DOI here).
    if search is None:
        search = fetch_mesa_software(timeout)
    release = search.get("release") if isinstance(search, dict) and "release" in search else None
    sdk = sdks.get(plat["sdk_key"]) if plat["sdk_key"] else None
    already = bool(env.get(config.MESA_DIR_ENV))
    return {
        "platform": plat,
        "already_installed": already,
        "current_mesa_dir": env.get(config.MESA_DIR_ENV) or None,
        "load_mesa": detect_load_mesa(),
        "latest_release": release,
        "recommended_sdk": sdk,
        "all_sdks": sdks,
        "sdk_sources": sources,
        "software_error": search.get("error") if isinstance(search, dict) else None,
        "references": {"install_docs": INSTALL_DOCS, "sdk_page": MESASDK_PAGE,
                       "sdk_concept_doi": _SDK_DOI_URL},
        "steps": [
            "1. Install the MESA SDK for your platform (recommended_sdk.download_url), then the build deps.",
            "2. Download + unpack the MESA release (latest_release.download_url) to a path WITHOUT spaces.",
            "3. Add a load_mesa shell function with mesa_write_load_mesa (sets MESA_DIR/MESASDK_ROOT, "
            "sources mesasdk_init.sh, OMP_NUM_THREADS, PATH, PS1).",
            "4. Open a new shell, run `load_mesa`, then `./install` inside $MESA_DIR (this can take a while).",
            "5. Verify with get_mesa_info.",
        ],
    }
