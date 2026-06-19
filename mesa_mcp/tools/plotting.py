"""FastMCP tools: render MESA history/profile plots (matplotlib, headless)."""
from __future__ import annotations

import os

from .. import plotting
from ..environment import build_env_context

try:  # Inline image content where the host supports it.
    from mcp.server.fastmcp import Image
except Exception:  # pragma: no cover
    Image = None


def _return_plot(res: dict):
    if res.get("error"):
        return res["error"]
    p = res["path"]
    note = f"Saved plot → {p}"
    if res.get("missing"):
        note += f"  (skipped missing columns: {res['missing']})"
    if Image is not None and p.lower().endswith(".png"):
        try:
            return [Image(path=p), note]
        except Exception:
            pass
    return note


def register(mcp) -> None:
    @mcp.tool()
    def mesa_plot_history(workspace: str, x: str = "model_number", y: str = "log_L",
                          preset: str = "", logx: bool = False, logy: bool = False):
        """Plot history.data columns and return the image inline (saves a PNG under
        `<workspace>/plots`). Use this instead of writing a plotting script.

        - `preset="hr"` draws the classic HR diagram (log L vs log Teff, Teff axis inverted) —
          conventions after A. Gautschy's SimpleMesaHRD, reimplemented on mesa_reader/matplotlib.
        - `preset="kippenhahn"` draws a Kippenhahn diagram (convective regions + core masses vs
          time) — needs conv_mx*_top/bot and *_core_mass columns in history.data.
        - Otherwise plot `y` (comma-separated for multiple series) versus `x`, e.g.
          x="star_age", y="log_L,log_Teff".

        Args:
            workspace: the work-folder path (must have LOGS/history.data).
            x: history column for the x-axis.
            y: history column(s) for the y-axis (comma-separated allowed).
            preset: "" or "hr".
            logx / logy: log-scale the axes.
        """
        return _return_plot(plotting.plot_history(build_env_context(), workspace, x, y, preset, logx, logy))

    @mcp.tool()
    def mesa_plot_profile(workspace: str, x: str = "mass", y: str = "logRho",
                          preset: str = "", profile_number: int = 0,
                          logx: bool = False, logy: bool = False):
        """Plot one saved profile's columns and return the image inline (PNG under
        `<workspace>/plots`).

        - `preset="abundance"` plots mass-fraction profiles of the common isotopes vs mass (log y).
        - Otherwise plot `y` (comma-separated) versus `x` (default mass).

        Args:
            workspace: the work-folder path (must have LOGS/profile*.data).
            x: profile column for the x-axis (default 'mass').
            y: profile column(s) for the y-axis (comma-separated allowed).
            preset: "" or "abundance".
            profile_number: which saved profile (0 = latest).
            logx / logy: log-scale the axes.
        """
        return _return_plot(plotting.plot_profile(build_env_context(), workspace, x, y, preset,
                                                  profile_number, logx, logy))
