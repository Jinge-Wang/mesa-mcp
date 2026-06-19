"""FastMCP tools: guide a fresh MESA installation (platform, downloads, load_mesa helper)."""
from __future__ import annotations

import json

from .. import installer
from ..environment import build_env_context


def register(mcp) -> None:
    @mcp.tool()
    def mesa_install_plan() -> str:
        """Produce a platform-aware MESA installation plan, as JSON: detected OS/arch, the latest
        MESA release and the **matching SDK** download (both from the MESA Zenodo community), whether
        MESA / a `load_mesa` helper are already present, and step-by-step instructions. Use this to
        help a user install MESA from scratch. The actual ~2 GB download + build is left to the user
        (or `mesa_execute_shell` with explicit consent); after building, add the shell helper with
        `mesa_install_set_env`."""
        return json.dumps(installer.installation_plan(build_env_context()), indent=2)

    @mcp.tool()
    def mesa_install_set_env(mesa_dir: str, mesasdk_root: str, confirm: bool = False,
                             omp_threads: int = 0) -> str:
        """Add a `load_mesa` shell function to the user's shell rc — the robust alternative to
        scattering raw `export`s. It sets `MESA_DIR`/`MESASDK_ROOT`, sources `mesasdk_init.sh`, sets
        `OMP_NUM_THREADS`, prepends `$MESA_DIR/scripts/shmesa` to PATH, and tags `PS1`.

        **Confirmation-gated:** with confirm=False (default) it returns a dry run (the exact text and
        target rc file) and writes nothing. With confirm=True it backs up the rc and appends the
        function. Refuses to add a duplicate if `load_mesa` already exists. After adding, the user
        opens a new shell and runs `load_mesa`.

        Args:
            mesa_dir: the MESA install path (must contain no spaces).
            mesasdk_root: the MESA SDK root path.
            confirm: True to actually write; False for a dry run.
            omp_threads: OMP_NUM_THREADS to set (0 = use the CPU core count).
        """
        res = installer.write_load_mesa(mesa_dir, mesasdk_root, confirm, omp_threads=omp_threads)
        return json.dumps(res, indent=2)
