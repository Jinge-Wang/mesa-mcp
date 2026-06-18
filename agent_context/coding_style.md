# Coding style — how code is written in this repo

Conventions specific to `mesa-mcp`. Match the existing `main.py` style; it is the reference for tone.

## Language & dependencies

- **Python 3.12** (repo pins `>=3.12`). Use modern typing freely.
- **Pure-Python and dependency-light.** Standard library first. Third-party deps are limited to
  `mcp`, `httpx`, `beautifulsoup4` (telemetry stays standard-library — no `pandas`). Adding any new dependency requires the
  user to run `uv add` themselves — see `rules.md`.

## Types & docstrings

- **Type hints on every function signature**, including return types.
- **Every `@mcp.tool` has an explicit, structured docstring.** It is the calling agent's only
  contract. State: what the tool does, when to use it, each argument, and the return shape. Follow
  the voice of the existing `get_mesa_info` / `set_openmp_threads` docstrings.
- Module-level and helper docstrings are one-line and purposeful (see `environment.py` helpers).

## Structure & modularity

- **`tools/` = thin FastMCP wrappers.** A tool function validates inputs, calls into a logic module,
  and formats the result. No business logic, scraping, or parsing lives in `tools/`.
- **Logic modules** hold the real work: `environment.py` (shell env), `shell.py` (execution),
  `version.py` (version detection), `docs/` (sources, fetch, index, search, test_suite),
  `knowledge/` (inlists, publications).
- `server.py` is the only place that constructs the `FastMCP` instance and registers tools. It
  exposes `main()`. `main.py` is a back-compat shim that calls it.
- Keep functions short and single-purpose. Prefer small pure functions that are easy to unit-test.

## FastMCP

- Use `FastMCP` decorators exclusively for tools/resources.
- Tools return strings (human/agent-readable) or structured JSON-serializable data — be consistent
  within a module and document the shape.

## Subprocess & environment

- Always build the environment via `build_env_context()`; never shell out with a bare environment.
- Use `subprocess.run(..., capture_output=True, text=True, timeout=...)` with a bounded timeout.
  Reuse the existing `run_command` helper where it fits.
- Relay stderr and non-zero exit codes into the result; never swallow errors.

## Networking

- Use `httpx` with explicit timeouts. Cache fetched docs/index data on disk (OS cache dir) keyed by
  version; cache scraped tables for the session.
- Local-first: check `$MESA_DIR/docs/source/` before any HTTP call.

## Output discipline

- Results feed an LLM context window. Rank, slice, and summarize; link to sources (file path or
  URL) instead of pasting whole files or sprawling tables.

## Naming

- `snake_case` for functions/variables, `CapWords` for classes, `UPPER_CASE` for module constants.
- Private helpers prefixed with `_` (consistent with `main.py`).
- Tool names are prefixed `mesa_…` and read as verbs (`mesa_search_docs`, `mesa_fetch_test_suite_index`).
