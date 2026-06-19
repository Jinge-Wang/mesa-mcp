"""FastMCP tools: extract key stellar properties from a run's history/profile."""
from __future__ import annotations

import json

from .. import analysis
from ..environment import build_env_context


def register(mcp) -> None:
    @mcp.tool()
    def mesa_analyze_history(workspace: str, star: str = "") -> str:
        """Summarize a run's evolutionary state from LOGS/history.data, as JSON: final
        model/age/L/Teff, core masses (He/C/O/Si/Fe where written), central abundances, current
        convective-core mixing, a coarse evolutionary-phase guess, and key transitions (e.g. the
        TAMS model where central hydrogen is depleted). Reports only columns the run actually wrote.

        For a **binary** run, set `star` to `"1"`/`"2"` (a component) or `"binary"`.

        Args:
            workspace: the work-folder path (must have LOGS/history.data).
            star: binary component selector — '1', '2', 'binary', or '' (single-star).
        """
        return json.dumps(analysis.analyze_history(build_env_context(), workspace, star), indent=2)

    @mcp.tool()
    def mesa_analyze_profile(workspace: str, profile_number: int = 0, star: str = "") -> str:
        """Analyze one saved profile (LOGS/profile*.data), as JSON: convective/overshoot/
        semiconvective/thermohaline mixing zones (as mass-coordinate intervals), central
        abundances, He/CO core-mass estimates, and active burning regions.

        For a **binary** run, set `star` to `"1"`/`"2"` to use that component's LOGS1/LOGS2 profiles.

        Args:
            workspace: the work-folder path (must have LOGS/profile*.data).
            profile_number: which saved profile (0 = latest).
            star: binary component selector — '1', '2', or '' (single-star).
        """
        return json.dumps(analysis.analyze_profile(build_env_context(), workspace, profile_number, star), indent=2)
