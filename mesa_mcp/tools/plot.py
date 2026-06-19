"""FastMCP tools — visualization (``mesa_plot_*``): matplotlib history/profile plots, headless
PGSTAR/pgbinary file output, viewing rendered images, and a live-refresh desktop window.
"""
from __future__ import annotations

import json
import os

from .. import live_view, plotting, viz
from ..environment import build_env_context

try:  # Inline image content where the host supports it.
    from mcp.server.fastmcp import Image
except Exception:  # pragma: no cover - older/newer SDKs
    Image = None

_RASTER = (".png", ".jpg", ".jpeg", ".gif")


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


def _format_enable(res: dict) -> str:
    if res.get("error"):
        return f"Could not enable plot file output: {res['error']}"
    lines = [f"Enabled plot file output in {res['workspace']} (kind: {res.get('kind')}) "
             f"→ {res['out_dir']}/"]
    for g in res.get("enabled", []):
        plots = ", ".join(g.get("plots") or []) or "(none)"
        note = f"  [{g['note']}]" if g.get("note") else ""
        lines.append(f"  &{g['namelist']} in {g['file']}: {plots}{note}")
    for c in res.get("changes", []):
        lines.append(f"   {c['file']} {c['control']}: {c['result']}")
    lines.append("Run the simulation, then view plots with mesa_plot_view(action='latest').")
    return "\n".join(lines)


def register(mcp) -> None:
    @mcp.tool()
    def mesa_plot_make(workspace: str, kind: str = "history", x: str = "", y: str = "",
                       preset: str = "", profile_number: int = 0, logx: bool = False,
                       logy: bool = False, star: str = ""):
        """Render a MESA plot to PNG (under `<workspace>/plots`) and return it inline. Two kinds:

        - `kind="history"` (default): plot history.data columns. Presets: `hr` (HR diagram),
          `kippenhahn` (convective regions + core masses). With `star="binary"` the default view is
          the `binary` preset (orbital period / separation / mass-transfer / RLOF from
          binary_history.data). Otherwise plot `y` (comma-separated) vs `x`
          (default x=`model_number`, y=`log_L`).
        - `kind="profile"`: plot one saved profile. Preset `abundance` (mass fractions vs mass).
          Otherwise plot `y` vs `x` (default x=`mass`, y=`logRho`); `profile_number` 0 = latest.

        For a **binary** run set `star` to `"1"`/`"2"` (a component) or `"binary"` (orbit, history).

        Args:
            workspace: the work-folder path.
            kind: 'history' or 'profile'.
            x, y: columns (comma-separated y allowed); blank = sensible default for the kind.
            preset: history: ''/'hr'/'kippenhahn'/'binary'; profile: ''/'abundance'.
            profile_number: (profile) which saved profile (0 = latest).
            logx / logy: log-scale the axes.
            star: binary component selector — '1', '2', 'binary', or '' (single-star).
        """
        env = build_env_context()
        k = kind.strip().lower()
        if k == "profile":
            res = plotting.plot_profile(env, workspace, x or "mass", y or "logRho", preset,
                                        profile_number, logx, logy, star)
        elif k == "history":
            res = plotting.plot_history(env, workspace, x or "model_number", y or "log_L", preset,
                                        logx, logy, star)
        else:
            return f"Unknown kind '{kind}'. Use 'history' or 'profile'."
        return _return_plot(res)

    @mcp.tool()
    def mesa_plot_view(workspace: str, action: str = "latest", limit: int = 20):
        """View rendered plot images in a workspace (PGSTAR/pgbinary file output or matplotlib
        plots). Two actions:

        - `action="latest"` (default): return the newest image inline (where the host renders
          images). Requires file output enabled + a run that produced plots (mesa_plot_pgstar) — the
          on-screen PGSTAR window does not work headless / in VS Code.
        - `action="list"`: list the images (newest first) with filename, inferred model number, path.

        Args:
            workspace: the work-folder path.
            action: 'latest' or 'list'.
            limit: (list) maximum entries to show (default 20).
        """
        act = action.strip().lower()
        if act == "list":
            res = viz.find_plots(workspace, limit)
            if res.get("error"):
                return res["error"]
            if not res["plots"]:
                return (f"No plot images in {res['workspace']}. Enable file output "
                        "(mesa_plot_pgstar) and run the simulation.")
            lines = [f"{res['count']} plot image(s) in {res['workspace']} (newest first):"]
            for p in res["plots"][:limit]:
                mdl = f"model {p['model']}" if p["model"] is not None else "model ?"
                lines.append(f"  {p['name']}  ({mdl})  {p['path']}")
            return "\n".join(lines)
        if act == "latest":
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
            return (f"Latest plot: {p}" + (f" (model {model})" if model is not None else "")
                    + " — open it to view.")
        return f"Unknown action '{action}'. Use 'latest' or 'list'."

    @mcp.tool()
    def mesa_plot_pgstar(workspace: str, plots: str = "", out_dir: str = "png",
                         interval: int = 10) -> str:
        """Enable headless plot **file** output so plots can be viewed where the on-screen window
        won't open (VS Code / remote / no X11). Sets `pgstar_flag` (&star_job) and, for a **binary**
        run, also `pgbinary_flag` (&binary_job), plus `<plot>_file_flag` / `_file_dir` /
        `_file_interval` for each window plot. The right inlist files are located from the resolved
        inlist chain. If `plots` is empty, auto-detects the plots already defined as windows
        (`*_win_flag`). After running, view with mesa_plot_view.

        Args:
            workspace: the work-folder path.
            plots: comma/space-separated plot prefixes (e.g. 'HR Grid1'); empty = auto-detect.
            out_dir: subdirectory for images (default 'png').
            interval: write a plot every N models (default 10).
        """
        return _format_enable(
            viz.enable_file_output(build_env_context(), workspace, plots, out_dir, interval))

    @mcp.tool()
    def mesa_plot_live(workspace: str, action: str = "open", interval: float = 2.0) -> str:
        """Open or close a separate, auto-refreshing desktop window that watches a workspace's plot
        directory and re-renders the newest PNG — so a run can be watched live even though PGSTAR's
        own on-screen window can't open in VS Code / headless sessions. It only reads the PNGs MESA
        writes (enable them with mesa_plot_pgstar), so it never conflicts with PGSTAR. Opening
        requires an on-screen display (see mesa_env_info's WINDOW_CAPABILITY).

        Args:
            workspace: the work-folder path being run.
            action: 'open' or 'close'.
            interval: (open) seconds between refreshes (default 2).
        """
        act = action.strip().lower()
        if act == "close":
            return json.dumps(live_view.stop_live_view(workspace), indent=2)
        if act == "open":
            return json.dumps(live_view.launch(build_env_context(), workspace, interval), indent=2)
        return json.dumps({"error": f"Unknown action '{action}'. Use 'open' or 'close'."}, indent=2)
