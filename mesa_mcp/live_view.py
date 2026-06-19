"""A self-contained, auto-refreshing image viewer for a running simulation's plots.

Because PGSTAR's on-screen window can't open from a headless/VS Code session, this opens a *separate*
GUI window (via the uv-managed matplotlib) that watches a workspace's plot directory and re-renders
the newest PNG every few seconds — so the user can watch a run live while MESA writes PGSTAR file
output. It only *reads* the PNGs MESA/our tools write, so it never conflicts with MESA's own PGSTAR
window.

Run standalone:  ``python -m mesa_mcp.live_view <workspace> [interval_s] [backend]``
Or detached via the ``launch``/``stop`` helpers used by the MCP tool.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys

from . import display, viz

STATE_NAME = ".mesa_liveview.json"
LOG_NAME = ".mesa_liveview.log"


def _newest_image(workspace: str) -> "str | None":
    res = viz.find_plots(workspace, limit=1)
    plots = res.get("plots") if isinstance(res, dict) else None
    return plots[0]["path"] if plots else None


def main(argv: list) -> int:
    if len(argv) < 2:
        print("usage: python -m mesa_mcp.live_view <workspace> [interval_s] [backend]")
        return 2
    workspace = argv[1]
    interval = float(argv[2]) if len(argv) > 2 else 2.0
    backend = argv[3] if len(argv) > 3 and argv[3] else None

    import matplotlib
    if backend:
        try:
            matplotlib.use(backend)
        except Exception:
            pass
    import matplotlib.image as mpimg
    import matplotlib.pyplot as plt

    plt.ion()
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.axis("off")
    fig.suptitle("MESA live view — waiting for plots…")
    fig.canvas.manager.set_window_title(f"MESA live view — {os.path.basename(workspace.rstrip('/'))}")

    current = None
    while plt.fignum_exists(fig.number):
        newest = _newest_image(workspace)
        if newest and newest != current:
            try:
                ax.clear()
                ax.axis("off")
                ax.imshow(mpimg.imread(newest))
                fig.suptitle(os.path.basename(newest))
                fig.canvas.draw_idle()
                current = newest
            except Exception:
                pass
        plt.pause(max(0.2, interval))
    return 0


# ---- detached launch / stop (used by the MCP tool) -----------------------------------------

def _read_state(ws: str) -> "dict | None":
    try:
        with open(os.path.join(ws, STATE_NAME), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def launch(env: dict, workspace: str, interval: float = 2.0) -> dict:
    """Open a detached live-view window watching ``workspace`` for the newest plot."""
    ws = os.path.abspath(os.path.expanduser(workspace))
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}

    cap = display.detect_display(env)
    if not cap["can_open_window"]:
        return {"error": "No on-screen display available — cannot open a live window.",
                "capability": cap,
                "hint": "Use mesa_plot_pgstar + mesa_plot_view to view plots headless."}

    state = _read_state(ws)
    if state and _pid_alive(state.get("pid", -1)):
        return {"error": f"A live view is already open here (pid {state['pid']}). "
                         "Close its window or call mesa_plot_live first."}

    full_env = dict(os.environ)
    full_env.update(env or {})
    logf = open(os.path.join(ws, LOG_NAME), "w", encoding="utf-8")
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "mesa_mcp.live_view", ws, str(interval),
             cap["recommended_backend"] or ""],
            cwd=ws, env=full_env, stdout=logf, stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL, start_new_session=True,
        )
    except Exception as e:
        return {"error": f"Failed to launch live view: {e}"}

    with open(os.path.join(ws, STATE_NAME), "w", encoding="utf-8") as f:
        json.dump({"pid": proc.pid, "backend": cap["recommended_backend"], "interval": interval}, f)
    return {"launched": True, "pid": proc.pid, "workspace": ws,
            "backend": cap["recommended_backend"], "interval": interval,
            "note": "A separate window opened on your desktop; it refreshes as new plots appear. "
                    "Close the window (or mesa_plot_live) to stop it."}


def stop_live_view(workspace: str) -> dict:
    ws = os.path.abspath(os.path.expanduser(workspace))
    state = _read_state(ws)
    if not state:
        return {"stopped": False, "note": "No live view recorded here."}
    pid = state.get("pid")
    if pid and _pid_alive(pid):
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except (OSError, ProcessLookupError):
            try:
                os.kill(pid, signal.SIGTERM)
            except (OSError, ProcessLookupError):
                pass
    try:
        os.remove(os.path.join(ws, STATE_NAME))
    except OSError:
        pass
    return {"stopped": True, "pid": pid}


if __name__ == "__main__":
    sys.exit(main(sys.argv))
