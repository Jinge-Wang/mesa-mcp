"""FastMCP tools — workspaces & inlist preparation (``mesa_work_*``).

Provision/list/clear work folders OUTSIDE the read-only MESA install, and edit/inspect inlists
(format-preserving, with the resolved inlist chain surfaced).
"""
from __future__ import annotations

from .. import cleanup, inlist as inlist_mod, workspace as workspace_mod
from ..environment import build_env_context


def _format_create(res: dict) -> str:
    if res.get("error"):
        return f"Could not create workspace: {res['error']}"
    lines = [
        f"Created workspace '{res['name']}' ({res['kind']} baseline: {res['baseline']})",
        f"  path:    {res['dest']}",
        f"  from:    {res['source']}",
        f"  inlists: {', '.join(res['inlists']) or '(none)'}",
        f"  files:   {', '.join(res['entries'])}",
        "",
        "Next: verify controls with mesa_docs_option, edit the inlists in place (patch, don't "
        "overwrite) with mesa_work_inlist_set, then build/run with mesa_env_shell (e.g. `./mk`) and "
        "mesa_run_start using this path as the working directory.",
    ]
    return "\n".join(lines)


def _format_list(res: dict) -> str:
    ws = res.get("workspaces", [])
    if not ws:
        return f"No workspaces under {res['root']} yet. Create one with mesa_work_create."
    lines = [f"Workspaces under {res['root']}:"]
    for w in ws:
        flag = " [has LOGS]" if w["has_LOGS"] else ""
        lines.append(f"  - {w['name']}{flag}  ({', '.join(w['inlists']) or 'no inlists'})")
        lines.append(f"      {w['path']}")
    return "\n".join(lines)


def _format_clean(res: dict) -> str:
    if res.get("error"):
        return f"Cannot clean: {res['error']}"
    if res.get("dry_run"):
        lines = [f"DRY RUN — would remove from {res['workspace']} (nothing deleted yet):"]
        for it in res["would_remove"]:
            kind = "dir " if it["is_dir"] else "file"
            lines.append(f"  [{kind}] {it['path']}  ({it['size']})")
        lines += ["", res["note"]]
        return "\n".join(lines)
    if not res.get("cleaned"):
        return res.get("note", "Nothing to clean.")
    lines = [f"Removed {len(res['removed'])} item(s) from {res['workspace']}:"]
    lines += [f"  - {p}" for p in res["removed"]]
    if res.get("errors"):
        lines.append("Errors:")
        lines += [f"  ! {e}" for e in res["errors"]]
    return "\n".join(lines)


def _format_set(res: dict) -> str:
    if res.get("error"):
        return f"Edit failed: {res['error']}"
    head = f"{res['action']}: {res['name']} = {res['value']}  (&{res['namelist']})"
    if res["action"] == "updated" and res.get("old_value") is not None:
        head += f"   [was: {res['old_value']}]"
    lines = [head]
    if res.get("note"):
        lines.append(f"  note: {res['note']}")
    if res.get("default") is not None:
        lines.append(f"  default for this control: {res['default']}")
    lines.append(f"  file:   {res['path']}")
    lines.append(f"  backup: {res['backup']}")
    if res.get("warning"):
        lines.append(f"  WARNING: {res['warning']}")
    return "\n".join(lines)


def _format_layout(lay: dict) -> list:
    """Render the resolved inlist chain + effective output locations."""
    lines = [f"Resolved inlist layout (kind: {lay['kind']}, entry: {lay['entry_inlist']}):"]
    for nl, files in lay.get("chains", {}).items():
        lines.append(f"  &{nl} read from: {' → '.join(files) if files else '(entry only)'}")

    def _star(label, st):
        lines.append(f"  {label}: log_directory='{st.get('log_directory')}', "
                     f"history='{st.get('history_name')}', photos='{st.get('photo_directory')}'")
    if lay.get("kind") == "binary":
        for k in ("1", "2"):
            st = (lay.get("stars") or {}).get(k)
            if st:
                _star(f"star {k} (entry {st.get('entry')})", st)
        b = lay.get("binary", {})
        lines.append(f"  binary: history='{b.get('history_name')}' in '{b.get('log_directory')}'")
    elif lay.get("star"):
        _star("star", lay["star"])
    return lines


def _format_settings(res: dict) -> str:
    if res.get("error"):
        return res["error"]
    lines = []
    if res.get("layout"):
        lines += _format_layout(res["layout"]) + [""]
    if res["count"] == 0:
        lines.append(f"No options are explicitly set in {', '.join(res['files'])} — everything uses "
                     "MESA defaults.")
        return "\n".join(lines).strip()
    lines += [
        f"Current inlist settings ({res['count']} set; files: {', '.join(res['files'])})",
        "Only explicitly-set options are shown; every other control uses its MESA default "
        "(query one with mesa_docs_option).",
        "",
    ]
    for nl, opts in res["namelists"].items():
        lines.append(f"&{nl}")
        for o in opts:
            units = f"  [{o['units']}]" if o["units"] else ""
            if not o["known"]:
                note = "  (⚠ unknown control — not in this MESA version)"
            elif o["default"] is not None:
                note = f"  (default: {o['default']})"
            else:
                note = ""
            lines.append(f"   {o['name']} = {o['value']}{units}{note}")
        lines.append("")
    return "\n".join(lines).strip()


def register(mcp) -> None:
    @mcp.tool()
    def mesa_work_create(name: str, baseline: str = "work", dest: str = "") -> str:
        """Provision a new MESA work folder OUTSIDE the read-only MESA install, copied from a
        baseline that you then edit and run. This is the safe way to start a simulation.

        Baselines:
          - 'work'   — the standard single-star work template (default).
          - 'binary' — the standard binary (two-star) work template.
          - a test-suite case name (e.g. '1.5M_with_diffusion') — replicate a verified setup
            with its real inlists (see mesa_docs_testsuite).

        Run outputs (LOGS, photos, caches) are not copied. After provisioning: verify any
        controls with mesa_docs_option, edit the inlists with mesa_work_inlist_set, then
        compile/run with mesa_env_shell + mesa_run_start using the returned path.

        Args:
            name: short workspace name (becomes the folder name under the workspace root).
            baseline: 'work', 'binary', or a test-suite case name.
            dest: optional absolute destination path (must be outside the MESA tree).
        """
        return _format_create(workspace_mod.create_workspace(build_env_context(), name, baseline, dest))

    @mcp.tool()
    def mesa_work_list() -> str:
        """List the MESA work folders already provisioned under the workspace root, with their
        inlists and whether each has run output (LOGS)."""
        return _format_list(workspace_mod.list_workspaces())

    @mcp.tool()
    def mesa_work_clear(workspace: str, confirm: bool = False) -> str:
        """Reset a workspace by removing only its run *output* — LOGS/, photos/, png/, top-level
        plot PNGs, and the detached-run state files. Inlists, src/, run_star_extras.f90, and
        make/ are left untouched, and paths inside the MESA install are refused.

        **Two-step + user confirmation.** Call with confirm=False first (default): it lists exactly
        what would be deleted and removes nothing. Get the user's go-ahead, then call again with
        confirm=True to delete. **Do NOT clean between phases of a multi-phase run** — later phases
        load models/photos that earlier phases saved.

        Args:
            workspace: the work-folder path (outside the MESA tree).
            confirm: must be True to actually delete; False performs a dry run.
        """
        return _format_clean(cleanup.clean_workspace(build_env_context(), workspace, confirm))

    @mcp.tool()
    def mesa_work_inlist_set(inlist_path: str, name: str, value: str, namelist: str = "") -> str:
        """Set a single control in a MESA inlist, **preserving formatting**. Updates an
        existing assignment (keeping its indentation and inline comment), uncomments a
        commented one, or inserts a new entry into the correct namelist before its closing
        `/`. Backs up the file to `<file>.bak` first, and refuses to edit anything inside
        `$MESA_DIR` (edit inlists in a workspace instead).

        If the target namelist isn't in the given file, the option is routed to the chain file that
        owns it (MESA assembles each namelist from a recursive `read_extra_*` chain), and the result
        notes the redirect. The control name is validated against the option reference (a warning is
        returned if unknown). `value` is written **verbatim**, so format it as Fortran expects
        (e.g. `1.5d0`, `.true.`, `'LOGS_MS'`) — verify with mesa_docs_option first.

        Args:
            inlist_path: path to the inlist file (must be outside the MESA tree).
            name: the control's exact LHS (e.g. 'initial_mass', "xa_central_lower_limit(1)").
            value: the new value, Fortran-formatted.
            namelist: optional namelist (e.g. 'controls'); inferred from the reference if omitted.
        """
        res = inlist_mod.set_option(build_env_context(), inlist_path, name, value, namelist or None)
        return _format_set(res)

    @mcp.tool()
    def mesa_work_inlist_show(path: str) -> str:
        """Show a workspace's **resolved inlist layout** (the entry inlist MESA reads, the
        `read_extra_*` chain per namelist, and the effective log/history/photo locations — which may
        be renamed, not the defaults) plus every option explicitly set, grouped by namelist, with
        each value, its MESA default, and units when known. Use this to review a configuration
        before running and to catch accidentally-set or hallucinated options (flagged as unknown).

        Args:
            path: an inlist file, or a workspace directory (all inlist* files are read; the layout is
                resolved for a directory).
        """
        return _format_settings(inlist_mod.show_settings(build_env_context(), path))
