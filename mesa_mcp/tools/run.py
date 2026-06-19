"""FastMCP tools: detached, non-blocking MESA runs and monitoring."""
from __future__ import annotations

import json

from .. import runner
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
            "mesa_stop_run.")


def _format_stop(res: dict) -> str:
    if res.get("error"):
        return f"Stop failed: {res['error']}"
    if not res.get("stopped"):
        return f"Not stopped: {res.get('note') or res.get('status')}"
    return f"Stopped run (pid {res['pid']})."


def register(mcp) -> None:
    @mcp.tool()
    def mesa_run(workspace: str, command: str = "./rn", on_existing: str = "warn") -> str:
        """Start a MESA run **detached** in a workspace and return immediately — it does NOT
        block, so a long or non-converging run never hangs the session. Output streams to
        `mesa_run.log` in the workspace; monitor with mesa_run_status and cancel with
        mesa_stop_run.

        **Get explicit user consent before calling this** (a run can take a long time). Compile
        first with mesa_execute_shell `./mk`; then run here. Only one run per workspace at a time.

        If a fresh `./rn` is requested but the workspace already holds run output (LOGS/, photos/),
        this refuses and lists what's there so you can decide WITH THE USER: clean first
        (mesa_clean_workspace) or proceed with `on_existing="continue"`. **Never clean a later phase
        of a multi-phase run** — it reuses models saved by earlier phases. A `./re` restart always
        proceeds (it needs the existing photos).

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
        history.data row as an aligned column→value map. Returning structured JSON (rather than
        MESA's line-wrapped terminal output) keeps the status compact and unambiguous to parse.

        A short raw `tail` is included only when `verbose=True`, or automatically when the run
        finished with a non-zero exit code (for debugging a failure).

        Args:
            workspace: the work-folder path where mesa_run was started.
            verbose: also include a short tail of the raw run log.
        """
        return json.dumps(runner.run_status(workspace, verbose=verbose), indent=2)

    @mcp.tool()
    def mesa_stop_run(workspace: str) -> str:
        """Stop the active detached run in a workspace (terminates its whole process group).

        Args:
            workspace: the work-folder path where the run is active.
        """
        return _format_stop(runner.stop_run(workspace))
