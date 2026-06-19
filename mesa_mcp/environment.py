"""Resolve and validate the user's MESA shell environment.

These helpers source the user's shell profile (loading global MESA variables and the
optional ``load_mesa`` helper), capture the resulting environment, and validate it so
MESA tools run with the correct MESA_DIR, SDK, and PATH. Ported from the original
main.py — this is the canonical implementation; build on it, do not rewrite it.
"""
from __future__ import annotations

import glob
import os
import platform
import re
import subprocess

from . import config


def detect_gyre(env: dict) -> dict:
    """Report whether the GYRE oscillation code is bundled with this MESA install.

    GYRE ships under ``$MESA_DIR/gyre`` but is a separate code (its own ``$GYRE_DIR`` + workflow);
    this MCP server does not yet drive GYRE — it only reports presence so the agent knows it's there.
    """
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    gyre_path = os.path.join(mesa_dir, "gyre") if mesa_dir else ""
    present = bool(gyre_path) and os.path.isdir(gyre_path)
    ver = None
    if present:
        tarballs = glob.glob(os.path.join(gyre_path, "gyre-*.tar.gz"))
        for t in tarballs:
            m = re.search(r"gyre-([\d.]+)\.tar\.gz$", os.path.basename(t))
            if m:
                ver = m.group(1)
                break
    return {"present": present, "path": gyre_path if present else None,
            "version": ver, "gyre_dir_env": env.get("GYRE_DIR", "") or None}

# Marker printed immediately before the `env` dump so the parser can skip any
# shell startup noise that precedes it.
_ENV_ANCHOR = "MESA_ENV_START"

# Sources the user's shell profile (loading global MESA variables), then runs the
# optional `load_mesa` helper if defined, and finally dumps the environment.
_PROBE_BODY = (
    "if type load_mesa >/dev/null 2>&1; then load_mesa >/dev/null 2>&1; fi; "
    "echo '" + _ENV_ANCHOR + "'; "
    "env"
)

# Process-wide override for the OpenMP thread count, injected into every command
# environment. Persists for the server lifetime.
_OMP_THREADS_OVERRIDE: int | None = None


def set_omp_threads_override(num_threads: int | None) -> None:
    """Set (or clear, with None) the session-wide OMP_NUM_THREADS override."""
    global _OMP_THREADS_OVERRIDE
    _OMP_THREADS_OVERRIDE = num_threads


def get_omp_threads_override() -> int | None:
    """Return the active OMP_NUM_THREADS override, or None if unset."""
    return _OMP_THREADS_OVERRIDE


def _candidate_shells() -> list:
    """Return the shells to try, ordered by platform preference.

    Honours $SHELL first when it is zsh/bash, then prefers zsh on macOS and bash
    on Linux, with the other as fallback.
    """
    candidates = []

    shell_env = os.environ.get("SHELL", "")
    if os.path.basename(shell_env) in ("zsh", "bash") and os.path.exists(shell_env):
        candidates.append(shell_env)

    preferred = ("zsh", "bash") if platform.system() == "Darwin" else ("bash", "zsh")
    for name in preferred:
        for path in (f"/bin/{name}", f"/usr/bin/{name}", f"/opt/homebrew/bin/{name}"):
            if os.path.exists(path) and path not in candidates:
                candidates.append(path)

    return candidates


def _rc_file_for(shell_path: str) -> str:
    """Return the profile file a given shell should source for user configuration."""
    home = os.path.expanduser("~")
    if os.path.basename(shell_path) == "bash":
        for rc in (".bashrc", ".bash_profile", ".profile"):
            candidate = os.path.join(home, rc)
            if os.path.exists(candidate):
                return candidate
        return os.path.join(home, ".bashrc")
    return os.path.join(home, ".zshrc")


def _parse_env_block(stdout: str) -> dict | None:
    """Parse the environment dump following the anchor, or None if MESA_DIR is absent."""
    parsed = {}
    inside_env_block = False
    for line in stdout.splitlines():
        if line.strip() == _ENV_ANCHOR:
            inside_env_block = True
            continue
        if inside_env_block and "=" in line:
            key, val = line.split("=", 1)
            parsed[key] = val
    return parsed if config.MESA_DIR_ENV in parsed else None


def source_shell_environment() -> dict:
    """Return the user's MESA environment by sourcing their shell profile.

    For each candidate shell, sources its profile to load global variables, runs the
    optional ``load_mesa`` helper if present, and captures the result. Falls back to
    the inherited process environment if no profile yields MESA_DIR.
    """
    for shell_path in _candidate_shells():
        rc_file = _rc_file_for(shell_path)
        command = f"source '{rc_file}' >/dev/null 2>&1; {_PROBE_BODY}"
        try:
            result = subprocess.run(
                [shell_path, "-c", command],
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=config.ENV_PROBE_TIMEOUT,
            )
        except Exception:
            continue

        parsed = _parse_env_block(result.stdout)
        if parsed is not None:
            return parsed

    return dict(os.environ)


def build_env_context() -> dict:
    """Return the MESA environment with the active OpenMP thread override applied."""
    env = source_shell_environment()
    if _OMP_THREADS_OVERRIDE is not None:
        env["OMP_NUM_THREADS"] = str(_OMP_THREADS_OVERRIDE)
    return env


def run_command(
    args: list,
    env_context: dict,
    merge_stderr: bool = False,
    timeout: int = config.COMMAND_TIMEOUT,
) -> str:
    """Run a command with the given environment and return its captured output."""
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=timeout, env=env_context
        )
        if result.returncode == 0:
            out = result.stdout.strip()
            if merge_stderr:
                out = (out + "\n" + result.stderr.strip()).strip()
            return out
        return f"Error (Code {result.returncode}): {result.stderr.strip()}"
    except Exception as e:
        return f"Execution Failed: {str(e)}"


def check_mesa_environment(env_context: dict) -> dict:
    """Validate that the environment satisfies MESA's build and runtime requirements."""
    issues = []

    try:
        if os.geteuid() == 0:
            issues.append("EUID_ROOT_PRIVILEGE_ERROR: MESA should not be run with root/sudo privileges.")
    except AttributeError:
        pass

    mesa_dir = env_context.get("MESA_DIR", "")
    if not mesa_dir:
        issues.append("MESA_DIR_NOT_SET: Environment variable MESA_DIR is empty.")
    elif " " in mesa_dir:
        issues.append("MESA_DIR_WHITESPACE_ERROR: Path contains spaces, which is unsupported by the build system.")
    elif not (os.path.isdir(os.path.join(mesa_dir, "star")) and os.path.isdir(os.path.join(mesa_dir, "const"))):
        issues.append("MESA_DIR_INVALID_STRUCTURE: Target path lacks expected star/const source directories.")

    if not env_context.get("MESA_DIR_INTENTIONALLY_EMPTY"):
        mesasdk_root = env_context.get("MESASDK_ROOT", "")
        if not mesasdk_root:
            issues.append("MESASDK_ROOT_NOT_SET: Environment variable MESASDK_ROOT is missing.")
        elif not os.path.isdir(mesasdk_root):
            issues.append(f"MESASDK_ROOT_INVALID_PATH: Directory path does not exist: {mesasdk_root}")

    return {"status": "VALID" if not issues else "INVALID", "issues": issues}
