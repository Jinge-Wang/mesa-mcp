"""FastMCP tools: provision and list MESA work folders (outside the MESA install)."""
from __future__ import annotations

from .. import cleanup, workspace
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
        "Next: verify controls with mesa_get_option, edit the inlists in place (patch, don't "
        "overwrite), then build/run with mesa_execute_shell (e.g. `./mk` or `make`, then `./rn`) "
        "using this path as the working directory.",
    ]
    return "\n".join(lines)


def _format_list(res: dict) -> str:
    ws = res.get("workspaces", [])
    if not ws:
        return f"No workspaces under {res['root']} yet. Create one with mesa_create_workspace."
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


def register(mcp) -> None:
    @mcp.tool()
    def mesa_create_workspace(name: str, baseline: str = "work", dest: str = "") -> str:
        """Provision a new MESA work folder OUTSIDE the read-only MESA install, copied from a
        baseline that you then edit and run. This is the safe way to start a simulation.

        Baselines:
          - 'work'   — the standard single-star work template (default).
          - 'binary' — the standard binary work template.
          - a test-suite case name (e.g. '1.5M_with_diffusion') — replicate a verified setup
            with its real inlists.

        Run outputs (LOGS, photos, caches) are not copied. After provisioning: verify any
        controls with mesa_get_option, edit the inlists in place, then compile/run with
        mesa_execute_shell using the returned path as the working directory.

        Args:
            name: short workspace name (becomes the folder name under the workspace root).
            baseline: 'work', 'binary', or a test-suite case name.
            dest: optional absolute destination path (must be outside the MESA tree).
        """
        return _format_create(workspace.create_workspace(build_env_context(), name, baseline, dest))

    @mcp.tool()
    def mesa_list_workspaces() -> str:
        """List the MESA work folders already provisioned under the workspace root, with their
        inlists and whether each has run output (LOGS)."""
        return _format_list(workspace.list_workspaces())

    @mcp.tool()
    def mesa_clean_workspace(workspace: str, confirm: bool = False) -> str:
        """Reset a workspace by removing only its run *output* — LOGS/, photos/, png/, top-level
        PGSTAR PNGs, and the detached-run state files. Inlists, src/, run_star_extras.f90, and
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
