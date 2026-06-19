# Implementation Phase Tracker

See [README.md](README.md) and `agent_context/architecture.md` for detail. Phases 5–8 were
(re)prioritized after multi-platform testing (Gemini CLI / Antigravity) surfaced safety and UX gaps:
agents created workspaces and ran simulations without confirmation, hallucinated inlist options,
and output was inconsistent/bloated across hosts.

| Phase | Core functional targets | Est. hours | Status |
| :--- | :--- | :--- | :--- |
| **Phase 0** | Design consolidation; revise guideline markdowns; `agent_context/` dev primer + root `AGENTS.md`. | 1–2 | ✅ Complete |
| **Phase 1** | Modular package; version/docs resolver; `mesa_search_docs` (ranked) + `mesa_fetch_doc_page`; `mesa_fetch_test_suite_index`/`details`; `mesa_execute_shell`; refactor info tools; runtime `mesa-agent` skill; basic Claude plugin + platform stubs + `install.sh`. | 6–8 | ✅ Complete |
| **Phase 2** | Web knowledge — done: `mesa_search_community_inlists` + `mesa_download_community_inlist` (session-purge) ✅, `mesa_search_publications` (Zenodo community API) ✅, `mesa_clear_downloads` ✅. Remaining: marketplace add-ons, optional `mesa_serve_docs`. (`known_bugs`/`developing` are already served by `mesa_fetch_doc_page`.) | 4–6 | 🔄 Core done |
| **Reference layer** | `mesa_get_option` + per-option search from the authoritative `*.defaults` files (controls/star_job/pgstar/eos/kap/binary/astero, ~2000 options). | 2–3 | ✅ Complete |
| **Phase 3** | Workspace orchestration: `mesa_create_workspace` (from a test-suite case, or the star/binary template) + `mesa_list_workspaces`, provisioned outside `$MESA_DIR` with run outputs excluded. Coupled multi-run orchestration deferred to Phase 5. | 6–8 | ✅ Core done |
| **Phase 4** | `mesa_set_inlist_option` (format-preserving patcher: update/uncomment/insert, backed up, sandboxed, validated against the option reference) + telemetry: `mesa_get_output_column` (master `*_columns.list`) and `mesa_read_history` (sliced/downsampled, pure stdlib — no pandas). | 4–5 | ✅ Complete |
| **Phase 5** | **Safe execution & visibility** (from testing feedback): skill guardrails — mandatory workspace-directory confirmation, mandatory run confirmation, no inlist-option hallucination (propose+confirm chosen values, add only relevant options, always patch never overwrite); `mesa_show_inlist_settings` (set options vs defaults, with units); units-in-comments on insert; trim `get_mesa_info` PATH. | 3–4 | 🔄 In progress |
| **Phase 6** | **Async, non-blocking runs & monitoring**: `mesa_run` (detached `./rn`/`./re` + PID + `mesa_run.log` + exit marker; Popen kept referenced), `mesa_run_status` (state, models written, tail), `mesa_stop_run` (process-group kill). Fixes the CLI hang and gives consistent bounded progress. | 4–5 | ✅ Complete |
| **Phase 7** | **Visualization**: `mesa_enable_pgstar_file_output` (auto-detects `*_win_flag` plots → file output), `mesa_latest_plot` (inline image) + `mesa_list_plots`; `PGSTAR_DISPLAY` diagnostic in get_mesa_info. The on-screen PGSTAR window can't open headless/in VS Code. | 3–4 | ✅ Complete |
| **Phase 8** | **Multi-platform marketplace & install**: `PLATFORMS.md` (support matrix + per-host setup); populated `gemini` + `antigravity` entries (MCP configs + READMEs) + portable `marketplace/mesa-agent.md` guidance; Gemini-CLI-obsolete note (→ Antigravity); `install.sh` writes all configs + prints per-host commands; anonymized example chat histories in `docs/`. (cursor/codex/copilot remain stubs.) | 4–6 | ✅ Complete |
| **Phase 9** | (1) Agent-driven **live auto-updating visualization window** for a running sim (re-render the newest PGSTAR file, or a watch-and-display loop; verify no conflict with MESA's own PGSTAR; detect X11/XQuartz on macOS + Linux). (2) **MESA installation toolset** (install this MCP first, then have the agent install MESA): detect OS/arch; fetch the latest MESA release + its Zenodo download; fetch the matching MESA SDK (Townsend page); guide install; with permission add a `load_mesa` function to the user's shell rc instead of raw global exports; server records that `load_mesa` exists. | TBD | 🔮 Planned |
| **Phase 2 remainder** | Marketplace add-ons; optional `mesa_serve_docs`. | 2–3 | ⬜ Not started |

## Notes (deferred ideas)

- **Simulation progress (% complete):** hard to estimate and deferred for now. MESA uses adaptive
  timesteps/resolution and the stopping condition varies (model number, stellar age, a central
  abundance, luminosity, …), so there's no reliable denominator. `mesa_run_status` reports
  models-written + the log tail (concrete progress) rather than a percentage. Revisit later.
- **Phase 9 — live visualization window:** let the agent open a window that auto-updates as the sim
  runs (watch the PGSTAR file dir and re-render the newest image, or a small viewer loop). Verify it
  doesn't conflict with MESA's own PGSTAR window. Add **X11/XQuartz detection** (macOS via XQuartz,
  Linux via an X server) so the agent knows whether an on-screen window is even possible — we support
  both macOS and Linux.
- **Phase 9 — MESA installation toolset:** a second toolset so a user can install this MCP server
  first and have the agent install MESA itself: detect the user's OS/arch; find the latest MESA
  release and its Zenodo download link; find the matching MESA SDK from
  `http://user.astro.wisc.edu/~townsend/static.php?ref=mesasdk`; walk the user through installation.
  The official SDK docs tell users to `export` globals directly (fragile) — instead, **with the
  user's permission, append a `load_mesa` function to their shell rc**: it sets `MESA_DIR` and
  `MESASDK_ROOT`, sources `$MESASDK_ROOT/bin/mesasdk_init.sh`, sets `OMP_NUM_THREADS`, adds
  `$MESA_DIR/scripts/shmesa` to PATH, and tags `PS1`. The server should **record that `load_mesa`
  exists** (e.g. surface it in `get_mesa_info`) so the agent is reminded to use it before running MESA.
