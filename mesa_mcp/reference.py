"""Parse MESA's ``*.defaults`` option-reference files into per-option records.

Files such as ``$MESA_DIR/star/defaults/controls.defaults`` are the authoritative source
for every inlist control: its namelist, default value, and documentation. They live in the
code (not just the docs tree), so they are available even when ``docs/`` is absent. Used by
the ``mesa_get_option`` lookup tool and to give ``mesa_search_docs`` per-option granularity.

Format of one option in a .defaults file::

      ! initial_mass
      ! ~~~~~~~~~~~~

      ! initial mass in Msun units.
      ! ::

    initial_mass = 1
"""
from __future__ import annotations

import glob
import os
import re

from . import config

# An option header is a single (optionally ``-quoted) word in a Fortran comment,
# immediately followed by a `~~~~` rule. Section headers use `====`/`----` instead.
_HEADER_RE = re.compile(r"^\s*!\s*`{0,2}([A-Za-z]\w*)(?:\([^)]*\))?`{0,2}\s*$")
_UNDERLINE_RE = re.compile(r"^\s*!\s*~{2,}\s*$")
# A default assignment line: `name = value` or `name(...) = value`.
_ASSIGN_RE = re.compile(r"^\s*([A-Za-z]\w*)\s*(?:\([^)]*\))?\s*=\s*(.+?)\s*$")
_COMMENT_RE = re.compile(r"^\s*!\s?(.*)$")

# Per-process memo: mesa_dir -> (signature, list[option]).
_MEMO: dict = {}


def defaults_files(mesa_dir: str) -> list:
    """Return the sorted list of ``*.defaults`` files across MESA's module defaults dirs."""
    if not mesa_dir:
        return []
    return sorted(glob.glob(os.path.join(mesa_dir, "*", "defaults", "*.defaults")))


def _namelist_for(stem: str) -> str:
    """Map a defaults filename stem to its namelist (drops the ``_dev`` suffix)."""
    return stem[:-4] if stem.endswith("_dev") else stem


def _scan_defaults(lines: list) -> dict:
    """Map every option name to its default from non-comment ``name = value`` lines."""
    defaults = {}
    for ln in lines:
        if ln.lstrip().startswith("!"):
            continue
        a = _ASSIGN_RE.match(ln)
        if a and a.group(1) not in defaults:
            defaults[a.group(1)] = a.group(2).split(" !", 1)[0].strip()
    return defaults


def parse_text(text: str, namelist: str, module: str, source: str) -> list:
    """Parse one .defaults file body into per-option records.

    Handles backtick-quoted names and stacked headers (several option names sharing one
    documentation block). Defaults are resolved from a global scan, so each name in a stack
    still gets its own value.
    """
    lines = text.splitlines()
    n = len(lines)
    defaults = _scan_defaults(lines)

    def header_at(k: int) -> "str | None":
        if k + 1 >= n:
            return None
        m = _HEADER_RE.match(lines[k])
        return m.group(1) if m and _UNDERLINE_RE.match(lines[k + 1]) else None

    options = []
    i = 0
    while i < n:
        if header_at(i) is None:
            i += 1
            continue

        # Collect a stack of consecutive headers that share the following doc block.
        stack = []
        while header_at(i) is not None:
            stack.append(header_at(i))
            i += 2

        # Collect the documentation up to the next header or the end of this block.
        doc_lines = []
        seen_assignment = False
        while i < n and header_at(i) is None:
            cm = _COMMENT_RE.match(lines[i])
            if cm:
                content = cm.group(1).rstrip()
                if content.strip() != "::":
                    doc_lines.append(content)
            elif lines[i].strip() == "":
                doc_lines.append("")
                if seen_assignment:
                    i += 1
                    break
            else:
                seen_assignment = True
            i += 1

        doc = "\n".join(doc_lines).strip()
        for name in stack:
            options.append({
                "name": name,
                "namelist": namelist,
                "module": module,
                "default": defaults.get(name),
                "doc": doc,
                "source": source,
            })
    return options


def _signature(files: list) -> dict:
    """Cheap fingerprint of the defaults files to detect staleness."""
    total = 0
    max_mtime = 0.0
    for f in files:
        try:
            st = os.stat(f)
        except OSError:
            continue
        total += st.st_size
        max_mtime = max(max_mtime, st.st_mtime)
    return {"count": len(files), "total": total, "max_mtime": round(max_mtime, 3)}


def build_options(env: dict) -> list:
    """Parse every option across the active install's .defaults files (memoized)."""
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    files = defaults_files(mesa_dir)
    if not files:
        return []
    sig = _signature(files)
    memo = _MEMO.get(mesa_dir)
    if memo and memo[0] == sig:
        return memo[1]

    options = []
    for path in files:
        stem = os.path.splitext(os.path.basename(path))[0]
        module = os.path.basename(os.path.dirname(os.path.dirname(path)))
        try:
            with open(path, "r", encoding="utf-8", errors="replace") as fh:
                text = fh.read()
        except OSError:
            continue
        options.extend(parse_text(text, _namelist_for(stem), module, path))

    _MEMO[mesa_dir] = (sig, options)
    return options


def lookup(env: dict, name: str, namelist: "str | None" = None) -> dict:
    """Return {'exact': [...], 'related': [...]} for ``name`` (optionally within a namelist)."""
    options = build_options(env)
    target = name.strip().lower()
    nl = namelist.strip().lower().lstrip("&") if namelist else None

    def ok_nl(o):
        return nl is None or o["namelist"].lower() == nl

    exact = [o for o in options if o["name"].lower() == target and ok_nl(o)]
    related = []
    if not exact:
        related = [o for o in options if target in o["name"].lower() and ok_nl(o)][:20]
    return {"exact": exact, "related": related}


def option_chunks(env: dict) -> list:
    """Convert parsed options into search-index chunks (title=name, heading=&namelist)."""
    mesa_dir = env.get(config.MESA_DIR_ENV, "") or os.sep
    chunks = []
    for o in build_options(env):
        body = o["doc"]
        if o["default"] is not None:
            body = f"{body}\n\ndefault: {o['name']} = {o['default']}"
        try:
            rel = os.path.relpath(o["source"], mesa_dir)
        except ValueError:
            rel = os.path.basename(o["source"])
        chunks.append({
            "path": rel,
            "title": o["name"],
            "heading": f"&{o['namelist']}",
            "text": body,
            "source": o["source"],
        })
    return chunks
