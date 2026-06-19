"""Assemble the FastMCP server, register all tools, and run over stdio."""
from __future__ import annotations

import signal
import sys

from mcp.server.fastmcp import FastMCP

from . import config, environment
from .tools import data, docs, env as env_tools, find, plot, run, work


def build_server() -> FastMCP:
    """Construct the FastMCP instance with every tool registered.

    Tools are organized into seven ``mesa_<area>_*`` families: env, docs, find, work, run, data, plot.
    """
    mcp = FastMCP("mesa-mcp-server")
    env_tools.register(mcp)
    docs.register(mcp)
    find.register(mcp)
    work.register(mcp)
    run.register(mcp)
    data.register(mcp)
    plot.register(mcp)
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
