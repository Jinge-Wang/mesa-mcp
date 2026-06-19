# Rules — non-negotiable guardrails

These are binding for any agent developing `mesa-mcp`. If the user explicitly overrides one, the
user wins — then update this file.

## 1. Safety & sandbox

- **MESA core is read-only.** Never create, modify, or delete anything under the MESA install
  (`$MESA_DIR`). Tools that write must target paths **outside** `$MESA_DIR`, and must verify this at
  runtime before writing.
- **Workspace separation.** All simulation building, inlist writing, and runs happen in isolated
  sibling work folders, never inside the MESA tree.
- **Session downloads are ephemeral.** Anything fetched from the network (community inlists, etc.)
  goes into a single session temp dir created at server startup and **purged on server exit**
  (register `atexit` + SIGINT/SIGTERM handlers). Don't bloat the user's disk.

## 2. Editing files (format stability)

- **No wholesale overwrites** of `inlist` files or `src/run_star_extras.f90`. Use precise block /
  line matching to insert or change fields.
- **Preserve Fortran namelist formatting:** indentation, `&namelist` headers, closing `/`,
  ampersands, comment style (`!`), and double-precision literals (`1.0d0`). Don't reflow untouched lines.

## 3. Dependencies & process

- **All Python dependencies are managed with `uv`.** Add packages with `uv add <pkg>` (which updates
  `pyproject.toml` + `uv.lock`); never `pip install` ad hoc into the environment.
- **Don't add dependencies silently.** Propose the exact `uv add` command and let the user run it
  (user preference). There's no stdlib-only restriction — add whatever a tool genuinely needs;
  `mesa_reader` is the canonical history/profile loader (with the stdlib parser in `columns.py` as a
  no-dep fallback), alongside `numpy`/`matplotlib` for analysis and plotting.

## 4. Prefer first-party over shmesa

- `shmesa` is optional and known-buggy. **No tool may depend on it.** Expose it only as a
  convenience the user/agent can call through `mesa_execute_shell`. Reliable behavior must come
  from our own code.

## 5. Local-first knowledge

- Read local `$MESA_DIR/docs/source/*.rst` before any network call. Network access is a **fallback**.
- Never scrape JS-rendered pages (Sphinx search, Zenodo records). Use local files, `searchindex.js`,
  or documented REST APIs.

## 6. Error handling & subprocess control

- **Fail fast and loud.** Capture and relay stderr / non-zero exit codes cleanly into the tool
  result. Never silence a failure.
- Subprocess calls use bounded timeouts and the environment from `build_env_context`. Long-running
  simulations (Phase 5) use detached, PID-tracked processes so tool calls never block the client.

## 7. Modularity

- `tools/` modules are **thin FastMCP wrappers**. Real logic lives in `environment.py`, `shell.py`,
  `docs/`, `knowledge/`. Keep functions short and focused.
- **Reuse, don't rewrite.** The existing `environment.py` helpers are correct — build on them.

## 8. Tool ergonomics for the calling agent

- Every `@mcp.tool` has full type hints and an explicit docstring stating what it does, when to use
  it, its args, and its return shape. The docstring is the calling agent's only spec — make it precise.
- Return context-efficient output. Don't dump giant ASCII tables or whole files into the result;
  summarize, slice, rank, and link.
