"""FastMCP tool: run the GYRE stellar-oscillation code on a MESA pulsation model."""
from __future__ import annotations

import json

from .. import gyre
from ..environment import build_env_context


def register(mcp) -> None:
    @mcp.tool()
    def mesa_run_gyre(workspace: str, inlist: str = "gyre.in", summary_file: str = "",
                      timeout: int = 600) -> str:
        """Run GYRE (stellar oscillations) on a pulsation model in a workspace and return the
        computed modes as JSON. Invokes `$GYRE_DIR/bin/gyre <inlist>` (or the bundled
        `$MESA_DIR/gyre`), bounded by `timeout`, then parses GYRE's text mode summary
        (l, n_pg, frequencies, …).

        **Prerequisites:** GYRE must be built and `$GYRE_DIR` set (see `mesa_get_info`'s GYRE line),
        a `gyre.in` inlist must exist in the workspace, and the MESA model must already be written as
        a GYRE pulsation file (the `astero` workflow / `write_pulse_data_*` controls — not yet
        configured by this server). If GYRE isn't available the tool returns clear guidance.

        Args:
            workspace: the work-folder path containing the GYRE inlist + pulsation model.
            inlist: the GYRE inlist filename (default `gyre.in`).
            summary_file: the summary filename to parse (default: auto-detect the run's output).
            timeout: seconds before aborting (default 600).
        """
        return json.dumps(
            gyre.run_gyre(build_env_context(), workspace, inlist, summary_file, timeout), indent=2)
