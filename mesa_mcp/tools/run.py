"""FastMCP tools: detached, non-blocking MESA runs and monitoring."""
from __future__ import annotations

from .. import runner
from ..environment import build_env_context


def _format_start(res: dict) -> str:
    if res.get("error"):
        return f"Could not start run: {res['error']}"
    return (f"Started `{res['command']}` detached (pid {res['pid']}) in {res['workspace']}.\n"
            f"Output → {res['log']}\n"
            "This returned immediately and does NOT block. Poll with mesa_run_status; cancel with "
            "mesa_stop_run.")


def _format_status(res: dict) -> str:
    if res.get("error"):
        return res["error"]
    badge = {
        "running": "RUNNING",
        "finished": f"FINISHED (exit {res['exit_code']})",
        "ended": "ENDED (process gone, no exit record)",
    }.get(res["status"], res["status"])
    lines = [f"Run: {badge}  |  `{res['command']}`  |  elapsed {res['elapsed_s']}s"]
    if res.get("models_written") is not None:
        lines.append(f"models in history.data: {res['models_written']}")
    lines.append(f"log: {res['log']}")
    if res.get("tail"):
        lines.append("--- last output ---")
        lines.extend(res["tail"])
    return "\n".join(lines)


def _format_stop(res: dict) -> str:
    if res.get("error"):
        return f"Stop failed: {res['error']}"
    if not res.get("stopped"):
        return f"Not stopped: {res.get('note') or res.get('status')}"
    return f"Stopped run (pid {res['pid']})."


def register(mcp) -> None:
    @mcp.tool()
    def mesa_run(workspace: str, command: str = "./rn") -> str:
        """Start a MESA run **detached** in a workspace and return immediately — it does NOT
        block, so a long or non-converging run never hangs the session. Output streams to
        `mesa_run.log` in the workspace; monitor with mesa_run_status and cancel with
        mesa_stop_run.

        **Get explicit user consent before calling this** (a run can take a long time). Compile
        first with mesa_execute_shell `./mk`; then run here. Only one run per workspace at a time.

        Args:
            workspace: the work-folder path (outside the MESA tree).
            command: the run command (default `./rn`; e.g. `./re` to restart).
        """
        return _format_start(runner.start_run(build_env_context(), workspace, command))

    @mcp.tool()
    def mesa_run_status(workspace: str) -> str:
        """Report a detached run's status: RUNNING / FINISHED (with exit code) / ENDED, the
        elapsed time, how many models have been written to history.data, and the last lines of
        output. Poll this to follow progress without blocking.

        Args:
            workspace: the work-folder path where mesa_run was started.
        """
        return _format_status(runner.run_status(workspace))

    @mcp.tool()
    def mesa_stop_run(workspace: str) -> str:
        """Stop the active detached run in a workspace (terminates its whole process group).

        Args:
            workspace: the work-folder path where the run is active.
        """
        return _format_stop(runner.stop_run(workspace))
