"""Fetch documentation content: local .rst → text, or network pages (cached).

httpx and BeautifulSoup are imported lazily so local-first features work without the
network dependencies installed. Run ``uv sync`` to enable network fetches.
"""
from __future__ import annotations

import hashlib
import os
import re

from .. import config

_MISSING_DEPS = (
    "Network features need httpx + beautifulsoup4, which aren't installed. Run "
    "`uv sync` (or `uv add httpx beautifulsoup4`) to enable them. Local docs remain available."
)


def _cache_file(url: str) -> str:
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:24]
    return os.path.join(config.cache_dir(), f"fetch-{digest}")


def http_get(url: str, cache: bool = True) -> str:
    """GET a URL and return the response text, caching the body on disk keyed by URL.

    Raises RuntimeError with install guidance if httpx is unavailable.
    """
    if cache:
        cached = _cache_file(url)
        if os.path.exists(cached):
            try:
                with open(cached, "r", encoding="utf-8") as f:
                    return f.read()
            except OSError:
                pass
    try:
        import httpx
    except ImportError as e:
        raise RuntimeError(_MISSING_DEPS) from e

    resp = httpx.get(url, timeout=config.HTTP_TIMEOUT, follow_redirects=True)
    resp.raise_for_status()
    text = resp.text
    if cache:
        try:
            with open(_cache_file(url), "w", encoding="utf-8") as f:
                f.write(text)
        except OSError:
            pass
    return text


_DIRECTIVE_RE = re.compile(r"^\s*\.\.\s+\S+::.*$")
_ROLE_RE = re.compile(r":[a-z_:]+:`([^`]*)`")


def rst_to_text(raw: str) -> str:
    """Lightly de-markup an .rst document into readable plain text for an agent."""
    lines = []
    for line in raw.splitlines():
        if _DIRECTIVE_RE.match(line):
            continue
        line = _ROLE_RE.sub(r"\1", line)
        line = line.replace("``", "`")
        lines.append(line)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()


def http_download(url: str, dest_path: str) -> int:
    """Stream a (possibly binary) URL to ``dest_path``; return the byte count.

    Used for record files (e.g. Zenodo downloads). Raises RuntimeError if httpx is missing.
    """
    try:
        import httpx
    except ImportError as e:
        raise RuntimeError(_MISSING_DEPS) from e

    total = 0
    with httpx.stream("GET", url, timeout=config.HTTP_TIMEOUT, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            for chunk in resp.iter_bytes():
                f.write(chunk)
                total += len(chunk)
    return total


def html_to_text(html: str) -> str:
    """Extract readable text from an HTML doc page (lazy BeautifulSoup import)."""
    try:
        from bs4 import BeautifulSoup
    except ImportError as e:
        raise RuntimeError(_MISSING_DEPS) from e
    soup = BeautifulSoup(html, "html.parser")
    main = soup.find("main") or soup.find("div", {"role": "main"}) or soup.body or soup
    for tag in main.find_all(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    return re.sub(r"\n{3,}", "\n\n", main.get_text("\n")).strip()
