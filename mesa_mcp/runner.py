"""Detached MESA runs with non-blocking status polling.

``start_run`` launches a command (e.g. ``./rn``) in a workspace, detached, writing output to
``mesa_run.log``; the call returns immediately so the agent/CLI never blocks on a long or
non-converging run. ``run_status`` reports progress (state, models written, log tail);
``stop_run`` terminates it. State lives in ``<workspace>/.mesa_run.json`` so it survives a
server restart, and an exit-code marker file records completion. Runs happen only in a
workspace OUTSIDE ``$MESA_DIR`` — and the caller must obtain user consent first (skill rule).
"""
from __future__ import annotations

import glob
import json
import os
import signal
import subprocess
import time

from . import columns, config
from .environment import _candidate_shells

LOG_NAME = "mesa_run.log"
STATE_NAME = ".mesa_run.json"
EXIT_NAME = ".mesa_run.exit"

# Live child processes by workspace, kept referenced so the Popen isn't garbage-collected
# (which can leave the detached child unsignalable). Lost on server restart — status then
# falls back to the on-disk exit-code marker + pid liveness.
_PROCS: dict = {}


def _is_within(child: str, parent: str) -> bool:
    if not parent:
        return False
    c = os.path.realpath(child)
    p = os.path.realpath(parent)
    return c == p or c.startswith(p + os.sep)


def _read_state(ws: str) -> "dict | None":
    try:
        with open(os.path.join(ws, STATE_NAME), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _write_state(ws: str, state: dict) -> None:
    try:
        with open(os.path.join(ws, STATE_NAME), "w", encoding="utf-8") as f:
            json.dump(state, f)
    except OSError:
        pass


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _status_of(ws: str, state: "dict | None") -> tuple:
    """Return (status, exit_code): running | finished(code) | ended(no record) | none."""
    proc = _PROCS.get(os.path.realpath(ws))
    if proc is not None:
        rc = proc.poll()
        return ("finished", rc) if rc is not None else ("running", None)

    exit_file = os.path.join(ws, EXIT_NAME)
    if os.path.exists(exit_file):
        try:
            with open(exit_file, "r", encoding="utf-8") as f:
                return "finished", int(f.read().strip())
        except (OSError, ValueError):
            return "finished", None
    if state and _pid_alive(state.get("pid", -1)):
        return "running", None
    if state:
        return "ended", None
    return "none", None


def _tail(path: str, n: int = 25, maxbytes: int = 65536) -> list:
    try:
        with open(path, "rb") as f:
            f.seek(0, os.SEEK_END)
            size = f.tell()
            f.seek(max(0, size - maxbytes))
            data = f.read().decode("utf-8", "replace")
    except OSError:
        return []
    return data.splitlines()[-n:]


def _models_written(ws: str) -> "int | None":
    try:
        res = columns.read_history({}, ws, last_n=1)
        return res.get("total_models") if "error" not in res else None
    except Exception:
        return None


def _existing_artifacts(ws: str) -> list:
    """Describe prior run output in ``ws`` (LOGS*/, photos*/, png/) — used to guard fresh runs."""
    found = []
    for logs in sorted(glob.glob(os.path.join(ws, "LOGS*"))):
        if os.path.isdir(logs):
            n = len(os.listdir(logs))
            if n:
                found.append(f"{os.path.basename(logs)}/ ({n} files)")
    for name in ("photos", "photos1", "photos2", "png"):
        p = os.path.join(ws, name)
        if os.path.isdir(p):
            n = len(os.listdir(p))
            if n:
                found.append(f"{name}/ ({n} files)")
    return found


def start_run(env: dict, workspace: str, command: str = "./rn",
              on_existing: str = "warn") -> dict:
    """Start ``command`` detached in ``workspace``; return immediately with the pid + log.

    ``on_existing`` governs a *fresh* run (``./rn``) when prior output already exists:
    ``"warn"`` (default) refuses and reports the artifacts so the caller can decide; ``"continue"``
    proceeds anyway (MESA appends/overwrites). A restart (``./re``) always proceeds — it needs the
    existing photos/models. This function NEVER deletes anything; cleanup is a separate,
    confirmation-gated tool.
    """
    ws = os.path.abspath(os.path.expanduser(workspace))
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    if not os.path.isdir(ws):
        return {"error": f"Workspace not found: {ws}"}
    if _is_within(ws, mesa_dir):
        return {"error": (f"Refusing to run inside the MESA install ({mesa_dir}). Run from a "
                          "workspace outside the MESA tree.")}

    state = _read_state(ws)
    status, _ = _status_of(ws, state)
    if status == "running":
        return {"error": (f"A run is already active here (pid {state['pid']}, "
                          f"`{state['command']}`). Use mesa_stop_run first, or wait.")}

    is_restart = os.path.basename(command.strip().split()[0] if command.strip() else "") == "re"
    if not is_restart and on_existing == "warn":
        existing = _existing_artifacts(ws)
        if existing:
            return {
                "needs_decision": True,
                "workspace": ws,
                "command": command,
                "existing": existing,
                "note": ("This workspace already has run output. A fresh `./rn` will run over it. "
                         "Decide WITH THE USER: clean first (mesa_clean_workspace, confirm-gated) "
                         "then re-run, or proceed as-is by re-calling with on_existing='continue'. "
                         "Do NOT clean if this is a later phase of a multi-phase run — it reuses "
                         "models saved by earlier phases (use `./re`/`./rn` without cleaning)."),
            }

    for marker in (EXIT_NAME,):
        p = os.path.join(ws, marker)
        if os.path.exists(p):
            try:
                os.remove(p)
            except OSError:
                pass

    log_path = os.path.join(ws, LOG_NAME)
    shells = _candidate_shells()
    shell = shells[0] if shells else "/bin/bash"
    wrapped = f"{command}; echo $? > '{EXIT_NAME}'"
    try:
        logf = open(log_path, "w", encoding="utf-8")
        proc = subprocess.Popen(
            [shell, "-c", wrapped],
            cwd=ws,
            env=env,
            stdout=logf,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        return {"error": f"Failed to start run: {e}"}

    _PROCS[os.path.realpath(ws)] = proc
    state = {"pid": proc.pid, "command": command, "log": log_path, "started": time.time()}
    _write_state(ws, state)
    return {"started": True, "pid": proc.pid, "command": command, "log": log_path, "workspace": ws}


def run_status(workspace: str, verbose: bool = False, tail: int = 25) -> dict:
    """Report run state as a structured dict: status, models written, and the latest model's
    full history columns (aligned key→value) — NOT the raw, line-wrapped terminal output.

    A short raw ``tail`` is included only when ``verbose`` is set, or when the run finished with a
    non-zero exit code (for error diagnosis), so normal polling stays compact.
    """
    ws = os.path.abspath(os.path.expanduser(workspace))
    state = _read_state(ws)
    if not state:
        return {"error": f"No run has been started in {ws}."}
    status, code = _status_of(ws, state)
    log_path = state.get("log") or os.path.join(ws, LOG_NAME)
    out = {
        "workspace": ws,
        "status": status,
        "exit_code": code,
        "command": state.get("command"),
        "elapsed_s": round(time.time() - state.get("started", time.time()), 1),
        "log": log_path,
        "models_written": _models_written(ws),
        "latest_model": columns.latest_model({}, ws),
    }
    if verbose or (code not in (None, 0)):
        out["tail"] = _tail(log_path, tail)
    return out


def _terminate(pid: int, sig: int) -> bool:
    """Signal the whole process group, falling back to the single pid in restricted envs."""
    try:
        os.killpg(os.getpgid(pid), sig)
        return True
    except (OSError, ProcessLookupError):
        try:
            os.kill(pid, sig)
            return True
        except (OSError, ProcessLookupError):
            return False


def stop_run(workspace: str) -> dict:
    """Terminate the active run (its whole process group, escalating SIGTERM → SIGKILL)."""
    ws = os.path.abspath(os.path.expanduser(workspace))
    key = os.path.realpath(ws)
    state = _read_state(ws)
    proc = _PROCS.get(key)
    if not state and proc is None:
        return {"error": f"No run to stop in {ws}."}
    status, _ = _status_of(ws, state)
    if status != "running":
        return {"stopped": False, "status": status, "note": "Run is not active."}

    pid = proc.pid if proc is not None else state.get("pid")
    _terminate(pid, signal.SIGTERM)
    time.sleep(0.5)
    if _pid_alive(pid):
        _terminate(pid, signal.SIGKILL)
        time.sleep(0.3)
    if proc is not None:
        try:
            proc.wait(timeout=2)
        except Exception:
            pass
        _PROCS.pop(key, None)
    if _pid_alive(pid):
        return {"stopped": False, "error": f"Could not terminate run (pid {pid})."}
    return {"stopped": True, "pid": pid}
