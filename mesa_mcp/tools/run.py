"""FastMCP tools — execute & monitor (``mesa_run_*``): detached non-blocking runs and GYRE."""
from __future__ import annotations

import json

from .. import gyre, runner
from ..environment import build_env_context


def _format_start(res: dict) -> str:
    if res.get("error"):
        return f"Could not start run: {res['error']}"
    if res.get("needs_decision"):
        lines = [f"Run NOT started — {res['workspace']} already has run output:"]
        lines += [f"  - {x}" for x in res["existing"]]
        lines.append("")
        lines.append(res["note"])
        return "\n".join(lines)
    return (f"Started `{res['command']}` detached (pid {res['pid']}) in {res['workspace']}.\n"
            f"Output → {res['log']}\n"
            "This returned immediately and does NOT block. Poll with mesa_run_status; cancel with "
            "mesa_run_stop.")


def _format_stop(res: dict) -> str:
    if res.get("error"):
        return f"Stop failed: {res['error']}"
    if not res.get("stopped"):
        return f"Not stopped: {res.get('note') or res.get('status')}"
    return f"Stopped run (pid {res['pid']})."


def register(mcp) -> None:
    @mcp.tool()
    def mesa_run_start(workspace: str, command: str = "./rn", on_existing: str = "warn") -> str:
        """Start a MESA run **detached** in a workspace and return immediately — it does NOT
        block, so a long or non-converging run never hangs the session. Output streams to
        `mesa_run.log` in the workspace; monitor with mesa_run_status and cancel with
        mesa_run_stop. Works for single-star and binary work folders (each has its own `./rn`).

        **Get explicit user consent before calling this** (a run can take a long time). Compile
        first with mesa_env_shell `./mk`; then run here. Only one run per workspace at a time.

        If a fresh `./rn` is requested but the workspace already holds run output, this refuses and
        lists what's there so you can decide WITH THE USER: clean first (mesa_work_clear) or proceed
        with `on_existing="continue"`. **Never clean a later phase of a multi-phase run** — it reuses
        models saved by earlier phases. A `./re` restart always proceeds (it needs the existing
        photos).

        Args:
            workspace: the work-folder path (outside the MESA tree).
            command: the run command (default `./rn`; e.g. `./re` to restart).
            on_existing: for a fresh run when output exists — `"warn"` (refuse + report) or
                `"continue"` (run anyway). Ignored for `./re`.
        """
        return _format_start(
            runner.start_run(build_env_context(), workspace, command, on_existing))

    @mcp.tool()
    def mesa_run_status(workspace: str, verbose: bool = False) -> str:
        """Report a detached run's status as **JSON**: `status` (running/finished/ended),
        `exit_code`, `elapsed_s`, `models_written`, and `latest_model` — the most recent
        history.data row as an aligned column→value map. For a **binary** run a `binary` block adds
        each component's model count and the latest `binary_history.data` (orbital) row. Returning
        structured JSON (rather than MESA's line-wrapped terminal output) keeps the status compact.

        A short raw `tail` is included only when `verbose=True`, or automatically when the run
        finished with a non-zero exit code (for debugging a failure).

        Args:
            workspace: the work-folder path where mesa_run_start was started.
            verbose: also include a short tail of the raw run log.
        """
        return json.dumps(runner.run_status(workspace, verbose=verbose), indent=2)

    @mcp.tool()
    def mesa_run_stop(workspace: str) -> str:
        """Stop the active detached run in a workspace (terminates its whole process group).

        Args:
            workspace: the work-folder path where the run is active.
        """
        return _format_stop(runner.stop_run(workspace))

    @mcp.tool()
    def mesa_run_gyre(workspace: str, inlist: str = "gyre.in", summary_file: str = "",
                      timeout: int = 600) -> str:
        """Run GYRE (stellar oscillations) on a pulsation model in a workspace and return the
        computed modes as JSON. Invokes `$GYRE_DIR/bin/gyre <inlist>` (or the bundled
        `$MESA_DIR/gyre`), bounded by `timeout`, then parses GYRE's text mode summary
        (l, n_pg, frequencies, …).

        **Prerequisites:** GYRE must be built and `$GYRE_DIR` set (see mesa_env_info's GYRE line),
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
