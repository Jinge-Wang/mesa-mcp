"""FastMCP tools: read-only access to MESA's bundled data libraries (data/)."""
from __future__ import annotations

import json

from .. import data_libs
from ..environment import build_env_context


def register(mcp) -> None:
    @mcp.tool()
    def mesa_list_data_libraries() -> str:
        """List MESA's bundled data libraries under `$MESA_DIR/data` (atmospheres, chem/isotopes,
        EOS, opacities, nuclear networks, rates, …) with a short description and file count, as
        JSON. Use this to discover what's available, then `mesa_load_data` to read a specific one.
        """
        return json.dumps(data_libs.list_libraries(build_env_context()), indent=2)

    @mcp.tool()
    def mesa_load_data(library: str, name: str = "") -> str:
        """Load a MESA data library (read-only), as JSON. Dedicated parsers:

        - `library="net"` — nuclear networks. No `name` → list available networks; `name="approx21"`
          → the isotopes and reaction handles that network includes (with includes resolved).
        - `library="solar"` — solar abundance pattern. `name="lodders09"` (default) / `"lodders03"`
          → per-isotope mass fractions.
        - `library="isotope"` — one isotope's properties. `name="c12"` → mass, Z, N, spin, mass excess.

        Any other library name that matches a `data/*_data` subdir lists its files (no parser yet).

        Args:
            library: 'net', 'solar', 'isotope', or a data subdir name (e.g. 'kap_data').
            name: the specific item within the library (network/pattern/isotope name).
        """
        return json.dumps(data_libs.load_data(build_env_context(), library, name), indent=2)
