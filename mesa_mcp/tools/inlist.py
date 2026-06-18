"""FastMCP tool: format-preserving inlist editing."""
from __future__ import annotations

from .. import inlist
from ..environment import build_env_context


def _format(res: dict) -> str:
    if res.get("error"):
        return f"Edit failed: {res['error']}"
    head = f"{res['action']}: {res['name']} = {res['value']}  (&{res['namelist']})"
    if res["action"] == "updated" and res.get("old_value") is not None:
        head += f"   [was: {res['old_value']}]"
    lines = [head]
    if res.get("default") is not None:
        lines.append(f"  default for this control: {res['default']}")
    lines.append(f"  file:   {res['path']}")
    lines.append(f"  backup: {res['backup']}")
    if res.get("warning"):
        lines.append(f"  WARNING: {res['warning']}")
    return "\n".join(lines)


def _format_settings(res: dict) -> str:
    if res.get("error"):
        return res["error"]
    if res["count"] == 0:
        return (f"No options are explicitly set in {', '.join(res['files'])} — everything uses "
                "MESA defaults.")
    lines = [
        f"Current inlist settings ({res['count']} set; files: {', '.join(res['files'])})",
        "Only explicitly-set options are shown; every other control uses its MESA default "
        "(query one with mesa_get_option).",
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
    def mesa_show_inlist_settings(path: str) -> str:
        """Show every option explicitly set in an inlist (or across all inlists in a workspace
        directory), grouped by namelist, with each value, its MESA default for comparison, and
        units when known. Unlisted controls use their defaults — query a specific one with
        mesa_get_option. Use this to review a configuration before running, and to catch
        accidentally-set or hallucinated options (flagged as unknown).

        Args:
            path: an inlist file, or a workspace directory (all inlist* files are read).
        """
        return _format_settings(inlist.show_settings(build_env_context(), path))

    @mcp.tool()
    def mesa_set_inlist_option(inlist_path: str, name: str, value: str, namelist: str = "") -> str:
        """Set a single control in a MESA inlist, **preserving formatting**. Updates an
        existing assignment (keeping its indentation and inline comment), uncomments a
        commented one, or inserts a new entry into the correct namelist before its closing
        `/`. Backs up the file to `<file>.bak` first, and refuses to edit anything inside
        `$MESA_DIR` (edit inlists in a workspace instead).

        The control name is validated against the option reference (a warning is returned if
        it's unknown). The `value` is written **verbatim**, so format it as Fortran expects
        (e.g. `1.5d0`, `.true.`, `'LOGS_MS'`) — verify with mesa_get_option first.

        Args:
            inlist_path: path to the inlist file (must be outside the MESA tree).
            name: the control's exact LHS (e.g. 'initial_mass', "xa_central_lower_limit(1)").
            value: the new value, Fortran-formatted.
            namelist: optional namelist (e.g. 'controls'); inferred from the reference if omitted.
        """
        res = inlist.set_option(build_env_context(), inlist_path, name, value, namelist or None)
        return _format(res)
