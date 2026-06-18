import os
import sys
import platform
import subprocess

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mesa-mcp-server")

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

# Process-wide override for the OpenMP thread count, set via set_openmp_threads
# and injected into every command environment. Persists for the server lifetime.
_OMP_THREADS_OVERRIDE: "int | None" = None


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


def _parse_env_block(stdout: str) -> "dict | None":
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
    return parsed if "MESA_DIR" in parsed else None


def source_shell_environment() -> dict:
    """Return the user's MESA environment by sourcing their shell profile.

    For each candidate shell, sources its profile to load global variables, runs
    the optional `load_mesa` helper if present, and captures the result. Falls
    back to the inherited process environment if no profile yields MESA_DIR.
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
                timeout=10,
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


def run_command(args: list, env_context: dict, merge_stderr: bool = False) -> str:
    """Run a command with the given environment and return its captured output."""
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=5, env=env_context)
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


@mcp.tool()
def get_mesa_info() -> str:
    """Report the MESA build environment: install paths, MESA version, gfortran
    version, OpenMP thread configuration, available CPU cores, kernel, and PATH.
    Use this first to confirm the toolchain is ready before compiling or running."""
    env_context = build_env_context()

    mesa_dir = env_context.get("MESA_DIR", "NOT_SET")
    mesasdk_root = env_context.get("MESASDK_ROOT", "NOT_SET")
    path_env = env_context.get("PATH", "NOT_SET")

    uname_info = run_command(["uname", "-a"], env_context)
    gfortran_info = run_command(["gfortran", "-v"], env_context, merge_stderr=True)
    if "gcc version" in gfortran_info:
        gfortran_clean = [line.strip() for line in gfortran_info.split("\n") if "gcc version" in line][-1]
    else:
        gfortran_clean = gfortran_info.strip() if gfortran_info.strip() else "NOT_FOUND"

    version_number = "UNKNOWN"
    if mesa_dir != "NOT_SET":
        version_file = os.path.join(mesa_dir, "data", "version_number")
        if os.path.exists(version_file):
            try:
                with open(version_file, "r") as f:
                    version_number = f.read().strip()
            except Exception:
                pass

    available_cores = os.cpu_count() or 0
    omp_threads = env_context.get("OMP_NUM_THREADS", "NOT_SET")

    env_status = check_mesa_environment(env_context)

    output_lines = [
        "--- MESA SYSTEM DIAGNOSTIC REPORT ---",
        f"ENVIRONMENT_STATUS: {env_status['status']}",
        f"MESA_VERSION: {version_number}",
        f"MESA_DIR: {mesa_dir}",
        f"MESASDK_ROOT: {mesasdk_root}",
        f"COMPILER_GFORTRAN: {gfortran_clean}",
        f"OMP_NUM_THREADS: {omp_threads}",
        f"AVAILABLE_CPU_CORES: {available_cores}",
        f"KERNEL_INFO: {uname_info}",
        "PATH_ELEMENTS:",
    ]
    for element in path_env.split(os.pathsep):
        if element.strip():
            output_lines.append(f"  - {element}")

    if env_status["issues"]:
        output_lines.append("CRITICAL_ERRORS:")
        for issue in env_status["issues"]:
            output_lines.append(f"  - {issue}")

    output_lines.append("--- END OF REPORT ---")
    return "\n".join(output_lines)


@mcp.tool()
def set_openmp_threads(num_threads: int) -> str:
    """Set the number of OpenMP threads (OMP_NUM_THREADS) MESA uses for compilation
    and runs. The value persists for this server session and is applied to all
    subsequent tool calls. Use to control parallelism; typically set to the number
    of available CPU cores reported by get_mesa_info."""
    global _OMP_THREADS_OVERRIDE

    if num_threads < 1:
        return f"Error: num_threads must be a positive integer, got {num_threads}."

    available_cores = os.cpu_count() or 0
    _OMP_THREADS_OVERRIDE = num_threads

    note = ""
    if available_cores and num_threads > available_cores:
        note = f" WARNING: requested {num_threads} exceeds {available_cores} available cores; oversubscription may degrade performance."

    return f"OMP_NUM_THREADS set to {num_threads} for this server session.{note}"


if __name__ == "__main__":
    initial_env = source_shell_environment()
    env_check = check_mesa_environment(initial_env)
    if env_check["status"] == "INVALID":
        print("[WARNING] MESA local pre-flight checks flagged infrastructure issues:", file=sys.stderr)
        for issue in env_check["issues"]:
            print(f"  * {issue}", file=sys.stderr)

    mcp.run()
