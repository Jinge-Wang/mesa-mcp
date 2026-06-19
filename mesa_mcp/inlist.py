"""Format-preserving editing of MESA inlist files.

Sets a single namelist control in place: updates an existing assignment (keeping its
indentation and inline comment), uncomments a commented one, or inserts a new entry into
the correct namelist before its closing ``/``. Never edits files inside ``$MESA_DIR``, and
backs up to ``<file>.bak`` first. Values are written verbatim — the caller is responsible
for Fortran formatting (see the inlist-namelist-rules skill reference). Unlike ``shmesa
change`` this preserves indentation and inline comments.
"""
from __future__ import annotations

import glob
import os
import re
import shutil

from . import config, reference

_NAMELIST_OPEN = re.compile(r"^\s*&(\w+)")
_NAMELIST_CLOSE = re.compile(r"^\s*/")
_SIBLING_ASSIGN = re.compile(r"^(\s*)[A-Za-z]\w*\s*(?:\([^)]*\))?\s*=")
# An active assignment line (used to read what's explicitly set in an inlist).
_SET_RE = re.compile(r"^\s*(?P<name>[A-Za-z]\w*(?:\([^)]*\))?)\s*=\s*(?P<val>[^!]*?)(?:\s*!(?P<cmt>.*))?$")


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


def _enclosing_namelist(lines: list, idx: int) -> "str | None":
    """The namelist (&name) that line ``idx`` sits inside, or None."""
    cur = None
    for j in range(min(idx + 1, len(lines))):
        mo = _NAMELIST_OPEN.match(lines[j])
        if mo:
            cur = mo.group(1)
        elif _NAMELIST_CLOSE.match(lines[j]):
            cur = None
    return cur


def _detect_indent(lines: list, open_i: int, close_i: int) -> str:
    for ln in lines[open_i + 1:close_i]:
        m = _SIBLING_ASSIGN.match(ln)
        if m:
            return m.group(1)
    return "   "  # MESA's conventional 3-space indent


def set_option(env: dict, inlist_path: str, name: str, value: str, namelist: "str | None" = None,
               _redirected: bool = False) -> dict:
    """Set ``name = value`` in an inlist, preserving format. Returns a result summary.

    If the target namelist isn't in the given file, the option is redirected to the chain file that
    owns it (resolved from the inlist include chain) rather than failing — MESA assembles each
    namelist from a recursive ``read_extra_*`` chain, so the control may live in another file.
    """
    path = os.path.abspath(os.path.expanduser(inlist_path))
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if _is_within(path, mesa_dir):
        return {"error": ("Refusing to edit a file inside the MESA install (read-only). Edit an "
                          "inlist in a workspace outside $MESA_DIR.")}
    if not os.path.isfile(path):
        return {"error": f"Inlist not found: {path}"}

    name = name.strip()
    value = value.strip()

    raw = open(path, "r", encoding="utf-8", errors="replace").read()
    ends_nl = raw.endswith("\n")
    lines = raw.splitlines()

    # Validate against the option reference; resolve the canonical namelist if not given. Some
    # controls (e.g. log_directory) exist in more than one namelist (&controls vs &binary_controls),
    # so when the reference is ambiguous, prefer the namelist whose block is present in THIS file.
    lookup = reference.lookup(env, name.split("(")[0], namelist)
    warning = None
    ref_nls = list(dict.fromkeys(o["namelist"] for o in lookup["exact"]))
    if namelist:
        canon_nl = namelist.strip().lstrip("&")
    elif len(ref_nls) == 1:
        canon_nl = ref_nls[0]
    elif len(ref_nls) > 1:
        canon_nl = next((nl for nl in ref_nls if _find_namelist(lines, nl)), ref_nls[0])
    else:
        canon_nl = None
        warning = (f"'{name}' was not found in this MESA version's option reference — writing it "
                   "anyway; double-check the name with mesa_docs_option.")
    target_nl = canon_nl

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
        # Report the namelist the line actually sits in (authoritative for an in-place edit).
        target_nl = _enclosing_namelist(lines, i) or target_nl
        break

    if action is None:  # insert into the namelist
        if not target_nl:
            return {"error": (f"'{name}' is not a known control and no namelist was given, so I "
                              "can't decide where to insert it. Pass namelist=… or check the name.")}
        block = _find_namelist(lines, target_nl)
        if block is None:
            # The namelist isn't in this file. Follow the inlist chain to the file that owns it.
            if not _redirected:
                from . import inlist_resolver
                ws = os.path.dirname(path)
                try:
                    entry = inlist_resolver.entry_inlist(ws)
                    owner = inlist_resolver.option_file(ws, entry, target_nl, name)
                except Exception:
                    owner = None
                if owner:
                    owner_path = os.path.abspath(os.path.join(ws, owner))
                    if owner_path != path and os.path.isfile(owner_path):
                        res = set_option(env, owner_path, name, value, namelist, _redirected=True)
                        if isinstance(res, dict) and "error" not in res:
                            res["redirected_from"] = os.path.basename(path)
                            res["note"] = (f"&{target_nl} isn't in {os.path.basename(path)}; wrote to "
                                           f"{os.path.basename(owner_path)} (the chain file that owns it).")
                        return res
            return {"error": (f"Namelist &{target_nl} not found in {os.path.basename(path)}. Its "
                              "controls may live in a different inlist (e.g. inlist_project).")}
        open_i, close_i = block
        indent = _detect_indent(lines, open_i, close_i)
        units = reference.units_for(lookup["exact"][0]["doc"]) if lookup["exact"] else None
        comment = f"  ! {units}" if units else ""
        lines.insert(close_i, f"{indent}{name} = {value}{comment}")
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


def read_settings(path: str) -> list:
    """Return the explicitly-set options in one inlist as [{namelist, name, value, comment}]."""
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    cur_nl = None
    out = []
    for ln in lines:
        mo = _NAMELIST_OPEN.match(ln)
        if mo:
            cur_nl = mo.group(1)
            continue
        if _NAMELIST_CLOSE.match(ln):
            cur_nl = None
            continue
        if not ln.strip() or ln.lstrip().startswith("!"):
            continue
        m = _SET_RE.match(ln)
        if m and cur_nl:
            out.append({
                "namelist": cur_nl,
                "name": m.group("name"),
                "value": m.group("val").strip(),
                "comment": (m.group("cmt") or "").strip(),
            })
    return out


def show_settings(env: dict, path: str) -> dict:
    """Summarize the options explicitly set across an inlist file or a workspace directory.

    For each set option, include its value, the MESA default, and units (when known) — so the
    user/agent can see exactly what is configured versus what is left at its default.
    """
    p = os.path.abspath(os.path.expanduser(path))
    if os.path.isdir(p):
        files = [f for f in sorted(glob.glob(os.path.join(p, "inlist*"))) if not f.endswith(".bak")]
    elif os.path.isfile(p):
        files = [p]
    else:
        return {"error": f"No inlist found at {p}."}
    if not files:
        return {"error": f"No inlist files under {p}."}

    namelists: dict = {}
    count = 0
    for f in files:
        for s in read_settings(f):
            look = reference.lookup(env, s["name"].split("(")[0])
            opt = look["exact"][0] if look["exact"] else None
            namelists.setdefault(s["namelist"], []).append({
                "name": s["name"],
                "value": s["value"],
                "default": opt["default"] if opt else None,
                "units": reference.units_for(opt["doc"]) if opt else None,
                "known": opt is not None,
                "file": os.path.basename(f),
            })
            count += 1

    # When pointed at a workspace directory, also surface the *resolved* inlist chain and effective
    # output locations, so the agent sees the real entry inlist / log dirs / history names MESA will
    # use (not assumed defaults).
    layout_info = None
    if os.path.isdir(p):
        try:
            from . import inlist_resolver
            lay = inlist_resolver.layout(p)
            nls = (["binary_job", "binary_controls", "pgbinary"] if lay.get("kind") == "binary"
                   else ["star_job", "controls", "pgstar"])
            layout_info = {
                "entry_inlist": lay["entry"],
                "kind": lay["kind"],
                "chains": {nl: inlist_resolver.chain_for(p, lay["entry"], nl) for nl in nls},
            }
            for key in ("star", "stars", "binary"):
                if key in lay:
                    layout_info[key] = lay[key]
        except Exception:
            layout_info = None

    return {"files": [os.path.basename(f) for f in files], "namelists": namelists,
            "count": count, "layout": layout_info}
