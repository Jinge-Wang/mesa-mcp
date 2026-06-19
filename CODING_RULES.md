# Developer Coding Rules

> **Canonical source:** [`agent_context/rules.md`](agent_context/rules.md). This page is a quick
> summary — when the two differ, `agent_context/rules.md` wins. New contributors (human or agent)
> should start at [AGENTS.md](AGENTS.md).

## The non-negotiables

1. **MESA core is read-only.** Never create/modify/delete anything under a MESA install
   (`$MESA_DIR`). Tools that write must target paths **outside** `$MESA_DIR` and verify it at runtime.
2. **Workspace separation.** All building, inlist writing, and runs happen in isolated sibling work
   folders, never inside the MESA tree.
3. **Patch, don't overwrite.** No wholesale rewrites of `inlist` or `run_star_extras.f90`. Make
   precise, format-preserving edits (keep indentation, `&`/`/`, `!` comments, `1.0d0` literals).
4. **Dependencies need user approval.** Never run `uv add`/`pip install` yourself — propose the
   exact command and `pyproject.toml` diff and stop.
5. **Prefer first-party over `shmesa`.** It's on PATH but known-buggy; no tool may depend on it.
6. **Local-first knowledge.** Read local `.rst` before the network; never scrape JS-rendered pages
   (use local files, `searchindex.js`, or REST APIs).
7. **Fail fast.** Relay stderr and non-zero exit codes; never silence failures. Long runs are
   detached and PID-tracked so tool calls don't block.
8. **Modularity.** `tools/` are thin FastMCP wrappers; logic lives in the supporting modules. Reuse
   the existing `environment.py` helpers rather than rewriting them.

## Stack

- **Python 3.12**, dependency-light (stdlib-first; scientific libs allowed where they pay off).
- Deps: `mcp[cli]`, `httpx`, `beautifulsoup4`, and (from Phase 10) `numpy`, `matplotlib`,
  `mesa_reader` for plotting/rates/analysis. Still **no `pandas`**.
- `FastMCP` decorators exclusively; full type hints and explicit tool docstrings.

See [`agent_context/coding_style.md`](agent_context/coding_style.md) for the full style guide.
