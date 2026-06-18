"""Resolve where MESA documentation lives for the active install.

Always keys off the live ``$MESA_DIR`` so re-pointing load_mesa to a different install
transparently changes both the version and the local docs path.
"""
from __future__ import annotations

import os

from .. import config, version


def local_docs_dir(env: dict) -> str | None:
    """Return ``$MESA_DIR/docs/source`` if it exists (the local .rst tree), else None."""
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if not mesa_dir:
        return None
    candidate = os.path.join(mesa_dir, "docs", "source")
    return candidate if os.path.isdir(candidate) else None


def network_base(env: dict) -> str:
    """Return the network docs base URL for the resolved version (trailing slash included)."""
    return f"{config.DOCS_HOST}/en/{version.docs_version(env)}/"


def describe_source(env: dict) -> dict:
    """Summarize the docs source: mode, local path (preferred), and network base URL."""
    local = local_docs_dir(env)
    return {
        "mode": "local" if local else "network",
        "local_dir": local,
        "network_base": network_base(env),
        "docs_version": version.docs_version(env),
    }
