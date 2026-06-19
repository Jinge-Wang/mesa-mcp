"""Assemble the FastMCP server, register all tools, and run over stdio."""
from __future__ import annotations

import signal
import sys

from mcp.server.fastmcp import FastMCP

from . import config, environment
from .tools import (
    analysis, community, data, execution, gyre, info, inlist, install, knowledge, plotting, rates,
    run, telemetry, viz, workspace,
)


def build_server() -> FastMCP:
    """Construct the FastMCP instance with every tool registered."""
    mcp = FastMCP("mesa-mcp-server")
    info.register(mcp)
    knowledge.register(mcp)
    community.register(mcp)
    workspace.register(mcp)
    inlist.register(mcp)
    telemetry.register(mcp)
    run.register(mcp)
    viz.register(mcp)
    rates.register(mcp)
    data.register(mcp)
    plotting.register(mcp)
    analysis.register(mcp)
    install.register(mcp)
    gyre.register(mcp)
    execution.register(mcp)
    return mcp


mcp = build_server()


def main() -> None:
    """Entry point: run a non-fatal env pre-flight, then serve over stdio."""
    initial_env = environment.source_shell_environment()
    env_check = environment.check_mesa_environment(initial_env)
    if env_check["status"] == "INVALID":
        print("[WARNING] MESA local pre-flight checks flagged infrastructure issues:", file=sys.stderr)
        for issue in env_check["issues"]:
            print(f"  * {issue}", file=sys.stderr)

    # Purge the session scratch dir on termination (atexit covers normal exit).
    def _terminate(_signum, _frame):
        config.cleanup_session()
        raise SystemExit(0)

    for _sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(_sig, _terminate)
        except (ValueError, OSError):
            pass

    mcp.run()


if __name__ == "__main__":
    main()
