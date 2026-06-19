"""FastMCP tools — environment & setup (``mesa_env_*``).

Diagnostics, shell execution in the sourced MESA env, OpenMP threads, and MESA install help.
"""
from __future__ import annotations

import json
import os

from .. import display, installer, shell, version
from ..docs import sources
from ..environment import (
    build_env_context,
    check_mesa_environment,
    detect_gyre,
    run_command,
    set_omp_threads_override,
)


def register(mcp) -> None:
    @mcp.tool()
    def mesa_env_info() -> str:
        """Report the MESA build environment: install path, MESA version and the
        documentation version/source it maps to, gfortran, OpenMP threads, CPU cores,
        kernel, shmesa availability, GYRE, on-screen-window capability, and PATH. Use this
        first to confirm the toolchain is ready before searching docs, compiling, or running."""
        env = build_env_context()
        mesa_dir = env.get("MESA_DIR", "NOT_SET")
        mesasdk_root = env.get("MESASDK_ROOT", "NOT_SET")
        path_env = env.get("PATH", "NOT_SET")

        uname_info = run_command(["uname", "-a"], env)
        gfortran_info = run_command(["gfortran", "-v"], env, merge_stderr=True)
        if "gcc version" in gfortran_info:
            gfortran_clean = [l.strip() for l in gfortran_info.split("\n") if "gcc version" in l][-1]
        else:
            gfortran_clean = gfortran_info.strip() or "NOT_FOUND"

        ver = version.describe_version(env)
        src = sources.describe_source(env)
        shmesa_path = run_command(["which", "shmesa"], env)
        shmesa = shmesa_path if shmesa_path.startswith("/") else "NOT_FOUND"
        pgstar_display = env.get("DISPLAY", "") or "not set (headless — use PGSTAR file output for plots)"
        display_cap = display.summary_line(env)
        load_mesa = installer.detect_load_mesa()
        load_mesa_str = (f"defined in {load_mesa['rc_file']}" if load_mesa["defined"]
                         else "not defined (use mesa_env_install action='set_env')")
        gyre = detect_gyre(env)
        if gyre["present"]:
            vtag = f" (v{gyre['version']})" if gyre["version"] else ""
            gdir = "set" if gyre["gyre_dir_env"] else "not set"
            gyre_str = f"bundled{vtag} at {gyre['path']}; GYRE_DIR {gdir} — run with mesa_run_gyre"
        else:
            gyre_str = "not bundled"

        available_cores = os.cpu_count() or 0
        omp_threads = env.get("OMP_NUM_THREADS", "NOT_SET")
        env_status = check_mesa_environment(env)

        lines = [
            "--- MESA SYSTEM DIAGNOSTIC REPORT ---",
            f"ENVIRONMENT_STATUS: {env_status['status']}",
            f"MESA_VERSION: {ver['raw']} ({'release' if ver['is_release'] else 'git/unversioned'})",
            f"MESA_DIR: {mesa_dir}",
            f"MESASDK_ROOT: {mesasdk_root}",
            f"DOCS_VERSION: {ver['docs_version']}",
            f"DOCS_SOURCE: {src['mode']} -> {src['local_dir'] or src['network_base']}",
            f"SHMESA: {shmesa} (optional; treat as best-effort, may be buggy)",
            f"PGSTAR_DISPLAY: {pgstar_display}",
            f"WINDOW_CAPABILITY: {display_cap}",
            f"LOAD_MESA: {load_mesa_str}",
            f"GYRE: {gyre_str}",
            f"COMPILER_GFORTRAN: {gfortran_clean}",
            f"OMP_NUM_THREADS: {omp_threads}",
            f"AVAILABLE_CPU_CORES: {available_cores}",
            f"KERNEL_INFO: {uname_info}",
        ]
        path_entries = [e for e in path_env.split(os.pathsep) if e.strip()]
        relevant = [e for e in path_entries if any(k in e.lower() for k in ("mesa", "sdk"))]
        lines.append(f"PATH_ENTRIES: {len(path_entries)} total"
                     + ("; MESA/SDK-related:" if relevant else " (none MESA-related)"))
        for element in relevant:
            lines.append(f"  - {element}")
        if env_status["issues"]:
            lines.append("CRITICAL_ERRORS:")
            for issue in env_status["issues"]:
                lines.append(f"  - {issue}")
        lines.append("--- END OF REPORT ---")
        return "\n".join(lines)

    @mcp.tool()
    def mesa_env_shell(command: str, path: str) -> str:
        """Run a shell command inside the user's sourced MESA environment (MESA_DIR, the
        SDK compilers, and shmesa are on PATH), with ``path`` as the working directory.

        Use for MESA workflows such as ``./mk``, ``./clean``, or ``shmesa …`` (for a long
        evolutionary run use ``mesa_run_start``, which is detached and non-blocking). The working
        directory MUST be a sibling workspace folder OUTSIDE the MESA installation — commands whose
        cwd is inside $MESA_DIR are rejected (MESA core is read-only). Output (stdout, stderr, exit
        code) is relayed verbatim. This call is bounded by a timeout.

        Args:
            command: the shell command line to execute.
            path: absolute path to the working directory (outside the MESA tree).
        """
        return shell.execute_shell(command, path)

    @mcp.tool()
    def mesa_env_threads(num_threads: int) -> str:
        """Set OMP_NUM_THREADS for MESA compilation and runs for this server session. The
        value persists and is applied to all subsequent tool calls. Typically set to the
        available CPU cores reported by mesa_env_info."""
        if num_threads < 1:
            return f"Error: num_threads must be a positive integer, got {num_threads}."
        available_cores = os.cpu_count() or 0
        set_omp_threads_override(num_threads)
        note = ""
        if available_cores and num_threads > available_cores:
            note = (f" WARNING: requested {num_threads} exceeds {available_cores} available "
                    "cores; oversubscription may degrade performance.")
        return f"OMP_NUM_THREADS set to {num_threads} for this server session.{note}"

    @mcp.tool()
    def mesa_env_install(action: str = "plan", mesa_dir: str = "", mesasdk_root: str = "",
                         confirm: bool = False, omp_threads: int = 0) -> str:
        """Help install MESA itself and wire up the shell. Two actions:

        - `action="plan"` (default): a platform-aware installation plan as JSON — detected OS/arch,
          the latest MESA release and the **matching SDK** (both from the MESA Zenodo community),
          whether MESA / a `load_mesa` helper are already present, and step-by-step instructions.
          The ~2 GB download + build is left to the user (or `mesa_env_shell` with explicit consent).
        - `action="set_env"`: add a `load_mesa` shell function to the user's shell rc (sets
          `MESA_DIR`/`MESASDK_ROOT`, sources `mesasdk_init.sh`, sets `OMP_NUM_THREADS`, prepends
          `$MESA_DIR/scripts/shmesa` to PATH, tags `PS1`). **Confirmation-gated:** `confirm=False`
          (default) returns a dry run and writes nothing; `confirm=True` backs up the rc and appends
          the function (refusing a duplicate). Requires `mesa_dir` + `mesasdk_root`.

        Args:
            action: "plan" or "set_env".
            mesa_dir: (set_env) the MESA install path (no spaces).
            mesasdk_root: (set_env) the MESA SDK root path.
            confirm: (set_env) True to write; False for a dry run.
            omp_threads: (set_env) OMP_NUM_THREADS to set (0 = use the CPU core count).
        """
        act = action.strip().lower()
        if act == "plan":
            return json.dumps(installer.installation_plan(build_env_context()), indent=2)
        if act in ("set_env", "setenv", "env"):
            if not mesa_dir or not mesasdk_root:
                return json.dumps({"error": "action='set_env' requires mesa_dir and mesasdk_root."},
                                  indent=2)
            return json.dumps(
                installer.write_load_mesa(mesa_dir, mesasdk_root, confirm, omp_threads=omp_threads),
                indent=2)
        return json.dumps({"error": f"Unknown action '{action}'. Use 'plan' or 'set_env'."}, indent=2)
