"""FastMCP tools: MESA environment and system diagnostics."""
from __future__ import annotations

import os

from .. import version
from ..docs import sources
from ..environment import (
    build_env_context,
    check_mesa_environment,
    run_command,
    set_omp_threads_override,
)


def register(mcp) -> None:
    @mcp.tool()
    def get_mesa_info() -> str:
        """Report the MESA build environment: install path, MESA version and the
        documentation version/source it maps to, gfortran, OpenMP threads, CPU cores,
        kernel, shmesa availability, and PATH. Use this first to confirm the toolchain is
        ready before searching docs, compiling, or running."""
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
            f"COMPILER_GFORTRAN: {gfortran_clean}",
            f"OMP_NUM_THREADS: {omp_threads}",
            f"AVAILABLE_CPU_CORES: {available_cores}",
            f"KERNEL_INFO: {uname_info}",
            "PATH_ELEMENTS:",
        ]
        for element in path_env.split(os.pathsep):
            if element.strip():
                lines.append(f"  - {element}")
        if env_status["issues"]:
            lines.append("CRITICAL_ERRORS:")
            for issue in env_status["issues"]:
                lines.append(f"  - {issue}")
        lines.append("--- END OF REPORT ---")
        return "\n".join(lines)

    @mcp.tool()
    def set_openmp_threads(num_threads: int) -> str:
        """Set OMP_NUM_THREADS for MESA compilation and runs for this server session. The
        value persists and is applied to all subsequent tool calls. Typically set to the
        available CPU cores reported by get_mesa_info."""
        if num_threads < 1:
            return f"Error: num_threads must be a positive integer, got {num_threads}."
        available_cores = os.cpu_count() or 0
        set_omp_threads_override(num_threads)
        note = ""
        if available_cores and num_threads > available_cores:
            note = (f" WARNING: requested {num_threads} exceeds {available_cores} available "
                    "cores; oversubscription may degrade performance.")
        return f"OMP_NUM_THREADS set to {num_threads} for this server session.{note}"
