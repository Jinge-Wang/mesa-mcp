"""FastMCP tool: execute commands in the sourced MESA environment."""
from __future__ import annotations

from .. import shell


def register(mcp) -> None:
    @mcp.tool()
    def mesa_execute_shell(command: str, path: str) -> str:
        """Run a shell command inside the user's sourced MESA environment (MESA_DIR, the
        SDK compilers, and shmesa are on PATH), with ``path`` as the working directory.

        Use for MESA workflows such as ``./mk``, ``./rn``, ``./clean``, or ``shmesa …``.
        The working directory MUST be a sibling workspace folder OUTSIDE the MESA
        installation — commands whose cwd is inside $MESA_DIR are rejected (MESA core is
        read-only). Output (stdout, stderr, exit code) is relayed verbatim. This call is
        bounded by a timeout; long evolutionary runs (detached) come in a later phase.

        Args:
            command: the shell command line to execute.
            path: absolute path to the working directory (outside the MESA tree).
        """
        return shell.execute_shell(command, path)
