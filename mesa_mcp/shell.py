"""Execute shell commands inside the user's sourced MESA environment.

Commands run with the environment from ``build_env_context()`` (so MESA_DIR, the SDK
compilers, and shmesa are on PATH) and a bounded timeout. The working directory is
sandbox-guarded to stay outside ``$MESA_DIR``, enforcing 'MESA core is read-only'.
Detached, PID-tracked long simulation runs are a later phase; this is for bounded commands.
"""
from __future__ import annotations

import os
import subprocess

from . import config
from .environment import _candidate_shells, build_env_context


def _is_within(child: str, parent: str) -> bool:
    """True if ``child`` is ``parent`` or nested inside it (compared by real path)."""
    if not parent:
        return False
    child_r = os.path.realpath(child)
    parent_r = os.path.realpath(parent)
    return child_r == parent_r or child_r.startswith(parent_r + os.sep)


def _truncate(text: str, limit: int = 6000) -> str:
    """Keep head and tail of long output so the context window isn't flooded."""
    if len(text) <= limit:
        return text
    head = text[: limit * 2 // 3]
    tail = text[-limit // 3:]
    return f"{head}\n…[{len(text) - limit} chars omitted]…\n{tail}"


def execute_shell(command: str, path: str, timeout: int = config.DEFAULT_SHELL_TIMEOUT) -> str:
    """Run ``command`` in ``path`` within the sourced MESA env; return a formatted result.

    Rejects working directories inside ``$MESA_DIR`` (sandbox). Relays stdout, stderr,
    and the exit code; never silences failures.
    """
    env = build_env_context()
    mesa_dir = env.get(config.MESA_DIR_ENV, "")

    work = os.path.abspath(os.path.expanduser(path)) if path else os.getcwd()
    if not os.path.isdir(work):
        return f"Error: working directory does not exist: {work}"
    if _is_within(work, mesa_dir):
        return (
            "SANDBOX_VIOLATION: refusing to run with a working directory inside the MESA "
            f"installation ({mesa_dir}). MESA core is read-only — run from a sibling work "
            "folder created outside the MESA tree."
        )

    shells = _candidate_shells()
    shell = shells[0] if shells else "/bin/bash"

    try:
        result = subprocess.run(
            [shell, "-c", command],
            cwd=work,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
            stdin=subprocess.DEVNULL,
        )
    except subprocess.TimeoutExpired:
        return (
            f"TIMEOUT after {timeout}s in {work}: `{command}`. For long simulation runs, "
            "use a detached run (planned for a later phase) rather than a blocking command."
        )
    except Exception as e:
        return f"Execution Failed: {e}"

    out = _truncate((result.stdout or "").strip())
    err = _truncate((result.stderr or "").strip())
    parts = [f"$ {command}", f"(cwd: {work})", f"exit_code: {result.returncode}"]
    if out:
        parts.append("--- stdout ---\n" + out)
    if err:
        parts.append("--- stderr ---\n" + err)
    if not out and not err:
        parts.append("(no output)")
    return "\n".join(parts)
