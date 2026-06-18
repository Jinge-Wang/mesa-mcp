"""Format-preserving editing of MESA inlist files.

Sets a single namelist control in place: updates an existing assignment (keeping its
indentation and inline comment), uncomments a commented one, or inserts a new entry into
the correct namelist before its closing ``/``. Never edits files inside ``$MESA_DIR``, and
backs up to ``<file>.bak`` first. Values are written verbatim — the caller is responsible
for Fortran formatting (see the inlist-namelist-rules skill reference). Unlike ``shmesa
change`` this preserves indentation and inline comments.
"""
from __future__ import annotations

import os
import re
import shutil

from . import config, reference

_NAMELIST_OPEN = re.compile(r"^\s*&(\w+)")
_NAMELIST_CLOSE = re.compile(r"^\s*/")
_SIBLING_ASSIGN = re.compile(r"^(\s*)[A-Za-z]\w*\s*(?:\([^)]*\))?\s*=")


def _is_within(child: str, parent: str) -> bool:
    if not parent:
        return False
    c = os.path.realpath(child)
    p = os.path.realpath(parent)
    return c == p or c.startswith(p + os.sep)


def _assign_re(key: str) -> "re.Pattern":
    """Match an assignment (active or commented) for the exact LHS ``key``."""
    k = re.escape(key)
    return re.compile(
        rf"^(?P<indent>\s*)(?P<bang>!\s*)?(?P<name>{k})(?P<eq>\s*=\s*)"
        rf"(?P<val>[^!\n]*?)(?P<cmt>\s*!.*)?$"
    )


def _find_namelist(lines: list, nl: str):
    """Return (open_index, close_index) for the ``&nl`` … ``/`` block, or None."""
    open_i = None
    for i, ln in enumerate(lines):
        m = _NAMELIST_OPEN.match(ln)
        if m and m.group(1) == nl:
            open_i = i
            continue
        if open_i is not None and _NAMELIST_CLOSE.match(ln):
            return open_i, i
    return None


def _detect_indent(lines: list, open_i: int, close_i: int) -> str:
    for ln in lines[open_i + 1:close_i]:
        m = _SIBLING_ASSIGN.match(ln)
        if m:
            return m.group(1)
    return "   "  # MESA's conventional 3-space indent


def set_option(env: dict, inlist_path: str, name: str, value: str, namelist: "str | None" = None) -> dict:
    """Set ``name = value`` in an inlist, preserving format. Returns a result summary."""
    path = os.path.abspath(os.path.expanduser(inlist_path))
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if _is_within(path, mesa_dir):
        return {"error": ("Refusing to edit a file inside the MESA install (read-only). Edit an "
                          "inlist in a workspace outside $MESA_DIR.")}
    if not os.path.isfile(path):
        return {"error": f"Inlist not found: {path}"}

    name = name.strip()
    value = value.strip()

    # Validate against the option reference; resolve the canonical namelist if not given.
    lookup = reference.lookup(env, name.split("(")[0], namelist)
    warning = None
    canon_nl = lookup["exact"][0]["namelist"] if lookup["exact"] else None
    if canon_nl is None:
        warning = (f"'{name}' was not found in this MESA version's option reference — writing it "
                   "anyway; double-check the name with mesa_get_option.")
    target_nl = namelist or canon_nl

    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    ends_nl = raw.endswith("\n")
    lines = raw.splitlines()

    rx = _assign_re(name)
    action = None
    old_value = None
    for i, ln in enumerate(lines):
        m = rx.match(ln)
        if not m:
            continue
        old_value = (m.group("val") or "").strip()
        action = "uncommented" if m.group("bang") else "updated"
        lines[i] = f"{m.group('indent')}{name}{m.group('eq')}{value}{m.group('cmt') or ''}"
        break

    if action is None:  # insert into the namelist
        if not target_nl:
            return {"error": (f"'{name}' is not a known control and no namelist was given, so I "
                              "can't decide where to insert it. Pass namelist=… or check the name.")}
        block = _find_namelist(lines, target_nl)
        if block is None:
            return {"error": (f"Namelist &{target_nl} not found in {os.path.basename(path)}. Its "
                              "controls may live in a different inlist (e.g. inlist_project).")}
        open_i, close_i = block
        indent = _detect_indent(lines, open_i, close_i)
        lines.insert(close_i, f"{indent}{name} = {value}")
        action = "inserted"

    shutil.copy2(path, path + ".bak")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + ("\n" if ends_nl else ""))

    return {
        "path": path,
        "name": name,
        "value": value,
        "old_value": old_value,
        "action": action,
        "namelist": target_nl,
        "backup": path + ".bak",
        "default": lookup["exact"][0]["default"] if lookup["exact"] else None,
        "warning": warning,
    }
