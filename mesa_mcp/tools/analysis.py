"""FastMCP tools: extract key stellar properties from a run's history/profile."""
from __future__ import annotations

import json

from .. import analysis
from ..environment import build_env_context


def register(mcp) -> None:
    @mcp.tool()
    def mesa_analyze_history(workspace: str) -> str:
        """Summarize a run's evolutionary state from LOGS/history.data, as JSON: final
        model/age/L/Teff, core masses (He/C/O/Si/Fe where written), central abundances, current
        convective-core mixing, a coarse evolutionary-phase guess, and key transitions (e.g. the
        TAMS model where central hydrogen is depleted). Reports only columns the run actually wrote.

        Args:
            workspace: the work-folder path (must have LOGS/history.data).
        """
        return json.dumps(analysis.analyze_history(build_env_context(), workspace), indent=2)

    @mcp.tool()
    def mesa_analyze_profile(workspace: str, profile_number: int = 0) -> str:
        """Analyze one saved profile (LOGS/profile*.data), as JSON: convective/overshoot/
        semiconvective/thermohaline mixing zones (as mass-coordinate intervals), central
        abundances, He/CO core-mass estimates, and active burning regions.

        Args:
            workspace: the work-folder path (must have LOGS/profile*.data).
            profile_number: which saved profile (0 = latest).
        """
        return json.dumps(analysis.analyze_profile(build_env_context(), workspace, profile_number), indent=2)
