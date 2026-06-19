"""Detect whether an on-screen GUI window can be opened on this host.

A MESA run's PGSTAR window (and our live viewer) needs a display. On macOS that's the native
Quartz window server (matplotlib ``macosx`` backend, no X11 needed) or XQuartz; on Linux it's an
X11/Wayland server (``$DISPLAY`` / ``$WAYLAND_DISPLAY``). This module reports the capability and a
recommended interactive matplotlib backend, used by ``mesa_env_info`` and the live-view tool.
"""
from __future__ import annotations

import os
import platform

# Interactive backends we may hand to the live viewer, in order of preference per platform.
_BACKENDS_MAC = ["macosx", "TkAgg", "QtAgg"]
_BACKENDS_LINUX = ["QtAgg", "TkAgg", "GTK3Agg"]


def _importable_backends(candidates: list) -> list:
    """Return the subset of candidate backends whose GUI toolkit actually imports."""
    ok = []
    for b in candidates:
        mod = {"macosx": "matplotlib.backends._macosx", "TkAgg": "tkinter",
               "QtAgg": "PyQt5", "GTK3Agg": "gi"}.get(b)
        try:
            __import__(mod) if mod else None
            ok.append(b)
        except Exception:
            continue
    return ok


def detect_display(env: "dict | None" = None) -> dict:
    """Report on-screen-window capability + a recommended matplotlib backend."""
    env = env or os.environ
    system = platform.system()
    display = env.get("DISPLAY", "")
    wayland = env.get("WAYLAND_DISPLAY", "")
    over_ssh = bool(env.get("SSH_CONNECTION") or env.get("SSH_TTY"))
    is_xquartz = bool(display) and ("xquartz" in display.lower() or display.startswith(":"))

    can_open = False
    backend = None
    notes = []

    if system == "Darwin":
        xquartz_installed = (is_xquartz or os.path.isdir("/opt/X11")
                             or os.path.exists("/Applications/Utilities/XQuartz.app"))
        # Native Quartz (macosx backend) works in a local Aqua session without X11.
        native_ok = not over_ssh
        candidates = _BACKENDS_MAC if native_ok else (["TkAgg"] if display else [])
        importable = _importable_backends(candidates)
        backend = importable[0] if importable else None
        can_open = bool(backend) and (native_ok or bool(display))
        if native_ok:
            notes.append("macOS local session: native Quartz windows available (macosx backend, no X11 needed).")
        if xquartz_installed:
            notes.append(f"XQuartz detected (DISPLAY={display or 'unset'}).")
        elif not native_ok:
            notes.append("Over SSH with no XQuartz/DISPLAY — no on-screen window. Use PGSTAR file output.")
    elif system == "Linux":
        importable = _importable_backends(_BACKENDS_LINUX)
        backend = importable[0] if importable else None
        can_open = bool(backend) and bool(display or wayland)
        if can_open:
            notes.append(f"Linux display present ({'Wayland' if wayland else 'X11'} "
                         f"{wayland or display}).")
        else:
            notes.append("No $DISPLAY/$WAYLAND_DISPLAY — headless. Use PGSTAR file output for plots.")
    else:
        notes.append(f"Unrecognized platform {system}; assuming headless.")

    return {
        "platform": system,
        "machine": platform.machine(),
        "display_env": display or wayland or "",
        "over_ssh": over_ssh,
        "xquartz_or_x11": is_xquartz or bool(display),
        "can_open_window": can_open,
        "recommended_backend": backend,
        "notes": notes,
    }


def summary_line(env: "dict | None" = None) -> str:
    """One-line capability summary for diagnostics."""
    d = detect_display(env)
    if d["can_open_window"]:
        return f"on-screen window OK (backend {d['recommended_backend']}, display {d['display_env'] or 'native'})"
    return "headless — no on-screen window; use PGSTAR file output / mesa_plot_view"
