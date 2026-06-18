"""FastMCP tools: surface PGSTAR plot images and enable headless file output."""
from __future__ import annotations

import os

from .. import viz
from ..environment import build_env_context

try:  # Inline image content where the host supports it.
    from mcp.server.fastmcp import Image
except Exception:  # pragma: no cover - older/newer SDKs
    Image = None

_RASTER = (".png", ".jpg", ".jpeg", ".gif")


def _format_enable(res: dict) -> str:
    if res.get("error"):
        return f"Could not enable PGSTAR file output: {res['error']}"
    lines = [
        f"Enabled PGSTAR file output in {res['workspace']}",
        f"  plots: {', '.join(res['plots'])}  →  {res['out_dir']}/",
        f"  &star_job: {res['star_job_file']}   &pgstar: {res['pgstar_file']}",
    ]
    for c in res["changes"]:
        lines.append(f"   {c['control']}: {c['result']}")
    lines.append("Run the simulation, then view plots with mesa_latest_plot.")
    return "\n".join(lines)


def register(mcp) -> None:
    @mcp.tool()
    def mesa_latest_plot(workspace: str):
        """Return the newest PGSTAR plot image from a workspace as an inline image (where the
        host renders images). Requires PGSTAR file output to be enabled and the run to have
        produced plots (see mesa_enable_pgstar_file_output) — the on-screen PGSTAR window does
        not work headless / in VS Code. Use mesa_list_plots for the list with model numbers.

        Args:
            workspace: the work-folder path.
        """
        res = viz.latest_plot(workspace)
        if res.get("error"):
            return res["error"]
        p = res["latest"]["path"]
        ext = os.path.splitext(p)[1].lower()
        if Image is not None and ext in _RASTER:
            try:
                return Image(path=p)
            except Exception:
                pass
        model = res["latest"]["model"]
        return f"Latest plot: {p}" + (f" (model {model})" if model is not None else "") + " — open it to view."

    @mcp.tool()
    def mesa_list_plots(workspace: str, limit: int = 20) -> str:
        """List the plot images in a workspace (newest first): filename, inferred model number,
        and path. View the newest with mesa_latest_plot.

        Args:
            workspace: the work-folder path.
            limit: maximum entries to show (default 20).
        """
        res = viz.find_plots(workspace, limit)
        if res.get("error"):
            return res["error"]
        if not res["plots"]:
            return (f"No plot images in {res['workspace']}. Enable PGSTAR file output "
                    "(mesa_enable_pgstar_file_output) and run the simulation.")
        lines = [f"{res['count']} plot image(s) in {res['workspace']} (newest first):"]
        for p in res["plots"][:limit]:
            mdl = f"model {p['model']}" if p["model"] is not None else "model ?"
            lines.append(f"  {p['name']}  ({mdl})  {p['path']}")
        return "\n".join(lines)

    @mcp.tool()
    def mesa_enable_pgstar_file_output(workspace: str, plots: str = "", out_dir: str = "png",
                                       interval: int = 10) -> str:
        """Enable PGSTAR file output (PNGs to disk) so plots can be viewed headless, where the
        on-screen window won't open (VS Code / remote / no X11). Sets `pgstar_flag` (&star_job)
        and `<plot>_file_flag` / `_file_dir` / `_file_interval` (&pgstar). If `plots` is empty,
        auto-detects the plots already defined as windows (`*_win_flag`). After running, view
        with mesa_latest_plot.

        Args:
            workspace: the work-folder path.
            plots: comma/space-separated plot prefixes (e.g. 'HR Grid1'); empty = auto-detect.
            out_dir: subdirectory for images (default 'png').
            interval: write a plot every N models (default 10).
        """
        return _format_enable(viz.enable_file_output(build_env_context(), workspace, plots, out_dir, interval))
