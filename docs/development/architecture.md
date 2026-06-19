# Architecture — module map & data flow

Living description of how `mesa-mcp` is organized. Update it when modules move or are added.

## Design principle

Two layers (a minimal MCP server plus guidance layers):

- **MCP server** = a small set of *deterministic* tools.
- **Guidance layers** = where the "intelligence" lives:
  - `docs/development/` for the agent **building** the server (dev-time).
  - `skills/mesa-agent/` for the agent **using** MESA at runtime (ships in the plugin).

## Package map (`mesa_mcp/`)

```
server.py        Builds the FastMCP instance, registers tools, exposes main().
config.py        Constants: docs base URL, OS cache dir, session temp dir, timeouts, env-var names.
environment.py   Sources the user's shell + load_mesa → MESA env; validation. (Moved from main.py.)
version.py       Detect MESA version from data/version_number → docs version (release vs hash).
shell.py         Bounded command execution in the sourced env (core of mesa_env_shell).
docs/
  sources.py     Resolve docs source: local $MESA_DIR/docs/source vs network base (live MESA_DIR).
  fetch.py       httpx fetch + on-disk cache; convert .rst → readable text.
  index.py       Build/cache a ranked search index over local .rst sections.
  search.py      Query the index → top-N; network searchindex.js fallback.
  test_suite.py  Parse test_suite.rst index + per-case .rst and real case dirs.
knowledge/        (Phase 2)
  inlists.py     Scrape mesastar.org marketplace inlists table; Zenodo DOI download → session temp.
  publications.py Query Zenodo community REST API for MESA publications.
runner.py        Detached MESA runs: start (guards a fresh run over existing output), JSON status
                 (state + latest_model history columns), stop. State in <ws>/.mesa_run.json.
cleanup.py       Confirmation-gated removal of a workspace's run output (LOGS*/photos*/png + run
                 state); refuses inside $MESA_DIR. Never touches inlists/src.
columns.py       Parse *_columns.list; read_history slices (stdlib); latest_model (last row →
                 {col: value}); load_mesa_data (canonical numpy-backed loader via mesa_reader).
rates.py         Parse data/rates_data REACLIB + reactions.list; evaluate a rate at T9; set_rate_factor
                 (wrap special_rate_factor array syntax via inlist.set_option).
data_libs.py     Read-only data/ access: list libraries; parse .net networks, Lodders abundances,
                 isotope properties, colors filters/models; structured inventory for the rest.
docs_server.py   Serve the local MESA docs over HTTP (detached); optional sphinx-build → cached HTML.
gyre.py          Run GYRE on a pulsation model (when built) + parse its text mode summary.
plotting.py      matplotlib (Agg) history/profile plots → PNG under <ws>/plots; presets hr
                 (credit Gautschy's SimpleMesaHRD) and abundance. Built on columns.load_mesa_data.
analysis.py      Extract stellar properties: analyze_history (core masses, central abundances,
                 phase, TAMS) and analyze_profile (mixing zones, abundances, burning regions).
display.py       Detect on-screen-window capability (macOS Quartz/XQuartz, Linux X11/Wayland) +
                 recommended matplotlib backend. Used by mesa_env_info and live_view.
live_view.py     Standalone auto-refreshing image viewer (watches a workspace's newest PNG) +
                 detached launch/stop helpers. Reads only files MESA writes — no PGSTAR conflict.
installer.py     MESA install help: detect_platform, fetch latest release + per-platform SDK from
                 the Zenodo software API, build/write a load_mesa shell function (confirm-gated).
inlist.py        Format-preserving inlist editing + read_settings; set_option redirects to the
                 chain file that owns a namelist (via inlist_resolver) when it's elsewhere.
inlist_resolver.py  Resolve the entry inlist (CLI arg → MESA_INLIST → 'inlist') + the recursive
                 read_extra_<ns>_inlist chain → real log_directory/star_history_name/photo_directory
                 (and binary inlist_names/history_name). layout() is consumed by columns/runner/viz/inlist.
reference.py     Parse *.defaults for authoritative option metadata (all namelists incl. binary).
viz.py           Surface PGSTAR/pgbinary plot images; enable headless file output (resolver-located files).
workspace.py     Provision/list work folders from baselines (outside $MESA_DIR).
tools/            Thin FastMCP wrappers (no logic) — seven mesa_<area>_* families:
  env.py         mesa_env_info, mesa_env_shell, mesa_env_threads, mesa_env_install(action).
  docs.py        mesa_docs_option, mesa_docs_search, mesa_docs_page, mesa_docs_testsuite(case),
                 mesa_docs_serve(action).
  find.py        mesa_find_search(source), mesa_find_download, mesa_find_clear.
  work.py        mesa_work_create, mesa_work_list, mesa_work_clear,
                 mesa_work_inlist_set, mesa_work_inlist_show.
  run.py         mesa_run_start, mesa_run_status, mesa_run_stop, mesa_run_gyre.
  data.py        mesa_data_history, mesa_data_column, mesa_data_analyze(kind),
                 mesa_data_library, mesa_data_rate(action).
  plot.py        mesa_plot_make(kind), mesa_plot_view(action), mesa_plot_pgstar, mesa_plot_live(action).

Binary runs: the telemetry/analysis/plotting tools take a `star` selector ('1'/'2' → each component,
'binary' → binary_history.data); the actual log dirs / filenames come from inlist_resolver.layout
(not assumed), threaded through columns._resolve_history_file / load_mesa_data. mesa_data_analyze and
mesa_plot_make have binary/orbital branches for star='binary'; mesa_plot_pgstar also enables &pgbinary.
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
