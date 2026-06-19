"""Project-wide constants and small path/config helpers.

Pure standard-library; no third-party imports so this module is always importable.
"""
from __future__ import annotations

import atexit
import os
import shutil
import tempfile

# --- environment variable names ---
MESA_DIR_ENV = "MESA_DIR"
DOCS_VERSION_ENV = "MESA_DOCS_VERSION"
WORKSPACE_ENV = "MESA_MCP_WORKSPACE"

# --- MESA documentation ---
DOCS_HOST = "https://docs.mesastar.org"
# Used when the local version_number is a git hash (no numbered release to map to).
DEFAULT_DOCS_VERSION = "latest"

# --- timeouts (seconds) ---
ENV_PROBE_TIMEOUT = 10      # sourcing the shell profile + load_mesa
COMMAND_TIMEOUT = 5         # quick info probes (uname, gfortran -v, ...)
DEFAULT_SHELL_TIMEOUT = 300  # mesa_env_shell default; bounded (async runs are Phase 5)
HTTP_TIMEOUT = 20.0         # network fallback fetches


def cache_dir() -> str:
    """Return the on-disk cache directory for mesa-mcp, creating it if missing.

    Honours $XDG_CACHE_HOME, else ~/.cache. Holds the docs search index and any
    persisted searchindex.js downloads (keyed by MESA version downstream).
    """
    base = os.environ.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    path = os.path.join(base, "mesa-mcp")
    os.makedirs(path, exist_ok=True)
    return path


def workspace_root() -> str:
    """Return the base directory for provisioned MESA work folders, created if missing.

    Honours $MESA_MCP_WORKSPACE, else ~/mesa-work. Work folders are created here, always
    OUTSIDE the read-only MESA installation.
    """
    root = os.environ.get(WORKSPACE_ENV) or os.path.join(os.path.expanduser("~"), "mesa-work")
    os.makedirs(root, exist_ok=True)
    return root


# --- session-scoped scratch space (purged on server exit) ---
_SESSION_DIR: "str | None" = None


def session_dir() -> str:
    """Return the per-session scratch directory, created lazily and purged on exit.

    Ephemeral network downloads (e.g. community inlists) land here so they never bloat
    the user's disk beyond the life of the server process.
    """
    global _SESSION_DIR
    if _SESSION_DIR is None or not os.path.isdir(_SESSION_DIR):
        _SESSION_DIR = tempfile.mkdtemp(prefix="mesa-mcp-session-")
        atexit.register(cleanup_session)
    return _SESSION_DIR


def cleanup_session() -> bool:
    """Remove the session scratch directory if it exists. Returns True if it was removed."""
    global _SESSION_DIR
    removed = bool(_SESSION_DIR) and os.path.isdir(_SESSION_DIR or "")
    if removed:
        shutil.rmtree(_SESSION_DIR, ignore_errors=True)
    _SESSION_DIR = None
    return removed
