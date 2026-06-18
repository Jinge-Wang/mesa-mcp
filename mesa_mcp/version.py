"""Detect the active MESA version and map it to a documentation version.

A Zenodo release writes a numbered string (e.g. ``r26.4.1``) to data/version_number;
a git checkout writes a commit hash (e.g. ``f12c70cf``). Numbered releases map to the
matching docs path (``/en/26.4.1/``); anything else falls back to ``/en/latest/``. The
MESA_DOCS_VERSION environment variable overrides the detected value.
"""
from __future__ import annotations

import os
import re

from . import config

_RELEASE_RE = re.compile(r"^r?\d+\.\d+(?:\.\d+)?$")


def read_version_number(mesa_dir: str) -> str | None:
    """Return the raw contents of $MESA_DIR/data/version_number, or None if unreadable."""
    if not mesa_dir:
        return None
    path = os.path.join(mesa_dir, "data", "version_number")
    try:
        with open(path, "r") as f:
            return f.read().strip()
    except OSError:
        return None


def is_release(raw: str | None) -> bool:
    """True if the version string looks like a numbered release (e.g. 'r26.4.1')."""
    return bool(raw) and bool(_RELEASE_RE.match(raw.strip()))


def _normalize(version_string: str) -> str:
    """Strip a leading release 'r' from a numbered version; pass others through."""
    s = version_string.strip()
    return s[1:] if is_release(s) and s.startswith("r") else s


def docs_version(env: dict) -> str:
    """Resolve the docs version to target for the active MESA install.

    Precedence: the MESA_DOCS_VERSION override (env context, then process env), then a
    numbered release parsed from data/version_number, else ``latest``.
    """
    override = env.get(config.DOCS_VERSION_ENV) or os.environ.get(config.DOCS_VERSION_ENV)
    if override:
        return _normalize(override)

    raw = read_version_number(env.get(config.MESA_DIR_ENV, ""))
    if is_release(raw):
        return _normalize(raw)
    return config.DEFAULT_DOCS_VERSION


def describe_version(env: dict) -> dict:
    """Return a summary: raw version_number, whether it is a release, and the docs version."""
    raw = read_version_number(env.get(config.MESA_DIR_ENV, ""))
    return {
        "raw": raw or "UNKNOWN",
        "is_release": is_release(raw),
        "docs_version": docs_version(env),
    }
