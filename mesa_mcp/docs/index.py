"""Build and query a ranked BM25 search index over the local MESA .rst docs.

The expensive step (walking ~40 MB of .rst and splitting into sections) is cached to
disk keyed by a content signature; BM25 statistics are recomputed in memory and memoized
per process. Tokenization splits underscore compounds so a natural-language query
("initial mass") matches a MESA control name (``initial_mass``).
"""
from __future__ import annotations

import json
import math
import os
import re

from .. import config, reference, version
from . import sources

_TOKEN_RE = re.compile(r"[a-z0-9_]+")
# RST section underline: a run (>=3) of a single punctuation char on its own line.
_UNDERLINE_RE = re.compile(r"^([=\-~^\"#*+:.'`])\1{2,}\s*$")
_ROLE_RE = re.compile(r":[a-z_:]+:`([^`]*)`")

_BM25_K1 = 1.5
_BM25_B = 0.75

# Per-process memo: local_dir -> (signature, LocalIndex)
_MEMO: dict = {}


def _tokenize(text: str) -> list:
    """Lowercase [a-z0-9_] tokens; underscore compounds also yield their parts."""
    tokens = []
    for tok in _TOKEN_RE.findall(text.lower()):
        tokens.append(tok)
        if "_" in tok:
            tokens.extend(p for p in tok.split("_") if p)
    return tokens


def _clean(text: str) -> str:
    """Strip common RST roles/markup and collapse whitespace for a preview snippet."""
    return re.sub(r"\s+", " ", _ROLE_RE.sub(r"\1", text)).strip()


def _split_sections(raw: str, rel_path: str) -> list:
    """Split one .rst document into section chunks: {path, title, heading, text}."""
    lines = raw.splitlines()
    chunks = []
    current_heading = ""
    buffer = []

    def flush():
        body = "\n".join(buffer).strip()
        if body or current_heading:
            chunks.append({"path": rel_path, "heading": current_heading, "text": body})

    i = 0
    while i < len(lines):
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if line.strip() and _UNDERLINE_RE.match(nxt) and len(nxt.strip()) >= len(line.strip()):
            flush()
            current_heading = line.strip()
            buffer = []
            i += 2
            continue
        buffer.append(line)
        i += 1
    flush()

    title = next((c["heading"] for c in chunks if c["heading"]),
                 os.path.splitext(os.path.basename(rel_path))[0])
    for c in chunks:
        c["title"] = title
    return chunks


def _build_chunks(local_dir: str) -> list:
    """Walk the local docs tree and return all section chunks across every .rst file."""
    chunks = []
    for root, _dirs, files in os.walk(local_dir):
        for fn in files:
            if not fn.endswith(".rst"):
                continue
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, local_dir)
            try:
                with open(full, "r", encoding="utf-8", errors="replace") as f:
                    raw = f.read()
            except OSError:
                continue
            # Skip .defaults-format reference files (e.g. reference/controls.rst); their
            # options are indexed per-option from the canonical .defaults files instead.
            if raw.lstrip().startswith("!"):
                continue
            chunks.extend(_split_sections(raw, rel))
    return chunks


def _signature(local_dir: str) -> dict:
    """Cheap content fingerprint (count, total size, max mtime) to detect staleness."""
    count = total = 0
    max_mtime = 0.0
    for root, _dirs, files in os.walk(local_dir):
        for fn in files:
            if not fn.endswith(".rst"):
                continue
            try:
                st = os.stat(os.path.join(root, fn))
            except OSError:
                continue
            count += 1
            total += st.st_size
            max_mtime = max(max_mtime, st.st_mtime)
    return {"count": count, "total": total, "max_mtime": round(max_mtime, 3)}


def _cache_path(version_str: str) -> str:
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", version_str)
    return os.path.join(config.cache_dir(), f"docs-index-{safe}.json")


def _load_chunks(env: dict, local_dir: str, sig: dict) -> list:
    """Return parsed chunks for ``local_dir``, using the on-disk cache when fresh."""
    cache_path = _cache_path(version.docs_version(env))
    try:
        with open(cache_path, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("signature") == sig and cached.get("local_dir") == local_dir:
            return cached["chunks"]
    except (OSError, json.JSONDecodeError, KeyError):
        pass

    chunks = _build_chunks(local_dir)
    try:
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump({"signature": sig, "local_dir": local_dir, "chunks": chunks}, f)
    except OSError:
        pass
    return chunks


def _snippet(text: str, q_terms: list, width: int = 240) -> str:
    """Return a cleaned snippet centered on the first matching query term."""
    cleaned = _clean(text)
    low = cleaned.lower()
    pos = -1
    for t in q_terms:
        pos = low.find(t)
        if pos != -1:
            break
    if pos == -1:
        return cleaned[:width] + ("…" if len(cleaned) > width else "")
    start = max(0, pos - width // 3)
    end = min(len(cleaned), start + width)
    return ("…" if start else "") + cleaned[start:end] + ("…" if end < len(cleaned) else "")


class LocalIndex:
    """In-memory BM25 index over parsed .rst section chunks."""

    def __init__(self, chunks: list, local_dir: str):
        self.chunks = chunks
        self.local_dir = local_dir
        self._titles = [c["title"].lower() for c in chunks]
        self._postings = []   # per-chunk {term: freq}
        self._lengths = []    # per-chunk token count
        self._df: dict = {}   # term -> number of chunks containing it
        for c in chunks:
            tf: dict = {}
            for t in _tokenize(f"{c['title']} {c['heading']} {c['text']}"):
                tf[t] = tf.get(t, 0) + 1
            self._postings.append(tf)
            self._lengths.append(sum(tf.values()) or 1)
            for t in tf:
                self._df[t] = self._df.get(t, 0) + 1
        self._n = len(chunks) or 1
        self._avgdl = (sum(self._lengths) / self._n) if self._lengths else 1.0

    def search(self, query: str, limit: int = 10) -> list:
        """Return the top-``limit`` chunks ranked by BM25 against ``query``."""
        q_terms = list(dict.fromkeys(_tokenize(query)))  # dedupe, keep order
        if not q_terms:
            return []
        scored = []
        for idx, tf in enumerate(self._postings):
            score = 0.0
            dl = self._lengths[idx]
            for t in q_terms:
                f = tf.get(t)
                if not f:
                    continue
                df = self._df.get(t, 0)
                idf = math.log(1 + (self._n - df + 0.5) / (df + 0.5))
                denom = f + _BM25_K1 * (1 - _BM25_B + _BM25_B * dl / self._avgdl)
                score += idf * (f * (_BM25_K1 + 1)) / denom
            if score > 0:
                # Boost an exact title hit (e.g. querying a control by its exact name).
                if self._titles[idx] in q_terms:
                    score *= 1.6
                scored.append((score, idx))
        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for score, idx in scored[:limit]:
            c = self.chunks[idx]
            results.append({
                "title": c["title"],
                "heading": c["heading"],
                "path": c["path"],
                "source": c.get("source") or os.path.join(self.local_dir, c["path"]),
                "score": round(score, 3),
                "snippet": _snippet(c["text"], q_terms),
            })
        return results


def get_local_index(env: dict) -> "LocalIndex | None":
    """Return a BM25 index over local docs **and** the option reference, or None if neither.

    The option reference (parsed per-option from the .defaults files) is included so that
    individual controls are searchable even when the narrative docs tree is absent.
    """
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    local_dir = sources.local_docs_dir(env)
    ref_files = reference.defaults_files(mesa_dir)
    if not local_dir and not ref_files:
        return None

    docs_sig = _signature(local_dir) if local_dir else {}
    combined = {"docs": docs_sig, "ref": reference._signature(ref_files), "dir": local_dir}
    key = mesa_dir or local_dir or "_"
    memo = _MEMO.get(key)
    if memo and memo[0] == combined:
        return memo[1]

    chunks = []
    if local_dir:
        chunks.extend(_load_chunks(env, local_dir, docs_sig))
    chunks.extend(reference.option_chunks(env))
    idx = LocalIndex(chunks, local_dir or mesa_dir)
    _MEMO[key] = (combined, idx)
    return idx
