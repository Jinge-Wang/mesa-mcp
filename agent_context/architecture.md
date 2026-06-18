# Architecture — module map & data flow

Living description of how `mesa-mcp` is organized. Update it when modules move or are added.

## Design principle

Two layers (a minimal MCP server plus guidance layers):

- **MCP server** = a small set of *deterministic* tools.
- **Guidance layers** = where the "intelligence" lives:
  - `agent_context/` for the agent **building** the server (dev-time).
  - `skills/mesa-agent/` for the agent **using** MESA at runtime (ships in the plugin).

## Package map (`mesa_mcp/`)

```
server.py        Builds the FastMCP instance, registers tools, exposes main().
config.py        Constants: docs base URL, OS cache dir, session temp dir, timeouts, env-var names.
environment.py   Sources the user's shell + load_mesa → MESA env; validation. (Moved from main.py.)
version.py       Detect MESA version from data/version_number → docs version (release vs hash).
shell.py         Bounded command execution in the sourced env (core of mesa_execute_shell).
docs/
  sources.py     Resolve docs source: local $MESA_DIR/docs/source vs network base (live MESA_DIR).
  fetch.py       httpx fetch + on-disk cache; convert .rst → readable text.
  index.py       Build/cache a ranked search index over local .rst sections.
  search.py      Query the index → top-N; network searchindex.js fallback.
  test_suite.py  Parse test_suite.rst index + per-case .rst and real case dirs.
knowledge/        (Phase 2)
  inlists.py     Scrape mesastar.org marketplace inlists table; Zenodo DOI download → session temp.
  publications.py Query Zenodo community REST API for MESA publications.
tools/            Thin FastMCP wrappers (no logic):
  info.py        get_mesa_info, set_openmp_threads.
  knowledge.py   mesa_search_docs, mesa_fetch_doc_page, mesa_fetch_test_suite_index/details.
  community.py   mesa_search_community_inlists, mesa_download_community_inlist, mesa_search_publications.
  execution.py   mesa_execute_shell.
```

## Core data flow

```
                       ┌─────────────────────────────┐
   tool call  ───────► │ environment.py              │  source shell + load_mesa → MESA env
                       │  build_env_context()        │
                       └──────────────┬──────────────┘
                                      │  $MESA_DIR (live)
                 ┌────────────────────┼─────────────────────┐
                 ▼                    ▼                     ▼
        ┌─────────────┐      ┌─────────────────┐    ┌───────────────┐
        │ version.py  │      │ docs/sources.py │    │ shell.py      │
        │ ver → docs  │      │ local rst? else │    │ run in env,   │
        │ version     │      │ network base    │    │ guard writes  │
        └─────────────┘      └────────┬────────┘    └───────────────┘
                                      │
                      local-first ┌───┴────┐ network fallback
                                  ▼        ▼
                         docs/index.py   docs/fetch.py (httpx + cache)
                         docs/search.py  + searchindex.js fallback
                         docs/test_suite.py
```

## Resolution rules (canonical)

- **Always follow the live `$MESA_DIR`.** A different active install changes both the version and
  the local docs path.
- **Version:** `data/version_number` → release (`r?\d+\.\d+(\.\d+)?`) uses that number; otherwise
  `latest`. `MESA_DOCS_VERSION` overrides.
- **Docs source:** prefer `$MESA_DIR/docs/source/`; fall back to `https://docs.mesastar.org/en/<ver>/`.
- **Caching:** built docs index → OS cache dir keyed by version + mtime; network `searchindex.js`
  → persisted on disk (reused across prompts); scraped tables → per session; downloads →
  session temp dir, purged on exit.

## Distribution

`marketplace/` follows a multi-platform plugin layout. `claude-code/mesa/` is populated (plugin manifest +
`.mcp.json` + the runtime skill). `cursor/`, `codex/`, `copilot-cli/`, `gemini/` are blank stubs
with `TODO.md` markers for future ports. `install.sh` handles macOS/Linux setup for the Claude/VS
Code path.
