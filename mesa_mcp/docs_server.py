"""Serve the installed MESA documentation as a local website.

A MESA install ships the Sphinx docs *source* at ``$MESA_DIR/docs/source`` (``.rst`` only — no
prebuilt HTML). This module serves those docs over a local HTTP server, detached so the tool call
never blocks:

- If a built HTML tree already exists (``docs/build/html``, ``docs/_build/html``, or our cache), it
  is served directly.
- ``rebuild=True`` builds the HTML with ``sphinx-build`` (best-effort; may take a few minutes and
  needs the docs' Sphinx requirements) into a version-keyed cache, then serves it.
- Otherwise the raw ``source/`` tree is served (browsable ``.rst``), with a pointer to the online
  docs.

State lives in ``<cache>/mesa_docs_server.json`` so the server can be stopped later.
"""
from __future__ import annotations

import json
import os
import shutil
import signal
import socket
import subprocess
import sys

from . import config, version

STATE_NAME = "mesa_docs_server.json"
BUILD_LOG = "mesa_docs_build.log"


def _state_path() -> str:
    return os.path.join(config.cache_dir(), STATE_NAME)


def _read_state() -> "dict | None":
    try:
        with open(_state_path(), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except (OSError, ProcessLookupError):
        return False
    return True


def _docs_source(mesa_dir: str) -> "str | None":
    src = os.path.join(mesa_dir, "docs", "source")
    return src if os.path.isdir(src) else None


def _existing_html(mesa_dir: str, cache_html: str) -> "str | None":
    for cand in (os.path.join(mesa_dir, "docs", "build", "html"),
                 os.path.join(mesa_dir, "docs", "_build", "html"),
                 cache_html):
        if os.path.isfile(os.path.join(cand, "index.html")):
            return cand
    return None


def _free_port(preferred: int) -> int:
    """Return ``preferred`` if free, else an OS-assigned free port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            pass
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _build_html(env: dict, source: str, out: str, timeout: int = 600) -> dict:
    """Run sphinx-build source → out (best-effort). Returns {ok, error?}."""
    if not shutil.which("sphinx-build", path=env.get("PATH", os.environ.get("PATH", ""))):
        return {"ok": False, "error": "sphinx-build not found on PATH (try `uv add sphinx` or use "
                                       "the online docs)."}
    os.makedirs(out, exist_ok=True)
    log = os.path.join(config.cache_dir(), BUILD_LOG)
    try:
        with open(log, "w", encoding="utf-8") as lf:
            proc = subprocess.run(["sphinx-build", "-b", "html", "-q", source, out],
                                  env=env, stdout=lf, stderr=subprocess.STDOUT, timeout=timeout)
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": f"sphinx-build timed out after {timeout}s.", "log": log}
    except Exception as e:
        return {"ok": False, "error": f"sphinx-build failed to start: {e}"}
    if proc.returncode != 0 or not os.path.isfile(os.path.join(out, "index.html")):
        return {"ok": False, "error": f"sphinx-build exited {proc.returncode}; see {log}.", "log": log}
    return {"ok": True}


def serve_docs(env: dict, port: int = 8000, rebuild: bool = False) -> dict:
    """Serve the local MESA docs over HTTP (detached). Returns the URL and what's being served."""
    mesa_dir = env.get(config.MESA_DIR_ENV, "")
    source = _docs_source(mesa_dir)
    if not source:
        return {"error": f"No docs/source under MESA_DIR ({mesa_dir or 'unset'}). "
                         "See the online docs at https://docs.mesastar.org/."}

    state = _read_state()
    if state and _pid_alive(state.get("pid", -1)):
        return {"error": f"A docs server is already running (pid {state['pid']}) at {state['url']}. "
                         "Stop it with mesa_docs_serve first."}

    ver = version.describe_version(env).get("docs_version", "latest")
    cache_html = os.path.join(config.cache_dir(), "mesa_docs_html", ver)

    built = False
    build_note = None
    serve_dir = _existing_html(mesa_dir, cache_html)
    if rebuild:  # build only on request — a full docs build can take minutes
        res = _build_html(env, source, cache_html)
        if res["ok"]:
            serve_dir = cache_html
            built = True
        else:
            build_note = res["error"]
    mode = "html" if serve_dir else "source"
    serve_dir = serve_dir or source

    bind_port = _free_port(port)
    try:
        proc = subprocess.Popen(
            [sys.executable, "-m", "http.server", str(bind_port), "--bind", "127.0.0.1",
             "--directory", serve_dir],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
    except Exception as e:
        return {"error": f"Failed to start docs server: {e}"}

    url = f"http://127.0.0.1:{bind_port}/"
    with open(_state_path(), "w", encoding="utf-8") as f:
        json.dump({"pid": proc.pid, "url": url, "serve_dir": serve_dir, "mode": mode}, f)

    note = ("Serving built HTML docs." if mode == "html" else
            "Serving the raw .rst source (unbuilt). Call again with rebuild=True to build browsable "
            "HTML (needs sphinx; can take a few minutes), or use https://docs.mesastar.org/.")
    if build_note:
        note = f"HTML build failed ({build_note}) — {note}"
    return {"url": url, "mode": mode, "serve_dir": serve_dir, "built": built,
            "pid": proc.pid, "note": note}


def stop_docs() -> dict:
    """Stop the local docs server if one is running."""
    state = _read_state()
    if not state:
        return {"stopped": False, "note": "No docs server is recorded."}
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
        os.remove(_state_path())
    except OSError:
        pass
    return {"stopped": True, "pid": pid, "url": state.get("url")}
