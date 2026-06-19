"""FastMCP tools: query MESA's nuclear reaction-rate data (JINA REACLIB)."""
from __future__ import annotations

import json

from .. import rates
from ..environment import build_env_context


def register(mcp) -> None:
    @mcp.tool()
    def mesa_get_reaction_rate(reaction: str, t9: float = 0.5) -> str:
        """Look up a MESA reaction by its handle (e.g. `r_c12_c12_to_he4_ne20`) and return its
        JINA REACLIB fit set(s) **evaluated at a temperature** — as JSON. Use this instead of
        hand-parsing the raw REACLIB file: it resolves the handle's isotopes via reactions.list,
        sums the matching REACLIB sets (resonant + non-resonant), and reports each set's 7 fit
        coefficients, source ("set label" → citation), Q-value, and rate.

        The rate is NA<σv> from the standard REACLIB formula; units depend on the number of
        reactants (1/s for a decay, cm^3 mol^-1 s^-1 for a 2-body reaction, …). To get a branching
        ratio, call this for each competing channel and compare `total_rate` (e.g. the alpha vs
        proton channels of carbon burning: `r_c12_c12_to_he4_ne20` vs `r_c12_c12_to_h1_na23`).

        If the handle isn't found, the result lists near-match `suggestions`. A reaction with no
        REACLIB set may be a weak/tabulated rate (weak_info.list / weakreactions.tables).

        Args:
            reaction: the MESA reaction handle (as in reactions.list).
            t9: temperature in 10^9 K (default 0.5).
        """
        return json.dumps(rates.get_reaction_rate(build_env_context(), reaction, t9), indent=2)

    @mcp.tool()
    def mesa_set_rate_factor(workspace: str, reaction: str, factor: float) -> str:
        """Scale a specific nuclear reaction's rate in a run by `factor`, hiding MESA's awkward
        `special_rate_factor` array syntax. Patches `reaction_for_special_factor(i)`,
        `special_rate_factor(i)`, and `num_special_rate_factors` into the &controls inlist
        (format-preserving, backed up) — reusing the slot if the reaction is already scaled, else
        appending the next index. Useful for sensitivity studies, e.g. boosting/suppressing the
        alpha channel of carbon burning: `reaction="r_c12_c12_to_he4_ne20", factor=1.5`.

        The reaction is validated against reactions.list (errors with `suggestions` if unknown).

        Args:
            workspace: the work-folder path, or the specific inlist file holding &controls.
            reaction: the MESA reaction handle to scale.
            factor: the multiplier (1.0 = unchanged).
        """
        res = rates.set_rate_factor(build_env_context(), workspace, reaction, factor)
        return json.dumps(res, indent=2)
