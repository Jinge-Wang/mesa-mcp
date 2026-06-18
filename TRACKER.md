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
| **Phase 8** | **Multi-platform marketplace & install**: populate `gemini` + `antigravity` (and `cursor`/`codex`/`copilot`) marketplace entries; note Gemini CLI is obsolete (→ Antigravity); platform support matrix + per-platform install instructions + the example chat histories in `docs/`. | 4–6 | ⬜ Not started |
| **Phase 2 remainder** | Marketplace add-ons; optional `mesa_serve_docs`. | 2–3 | ⬜ Not started |

## Notes (deferred ideas)

- **Simulation progress (% complete):** hard to estimate and deferred for now. MESA uses adaptive
  timesteps/resolution and the stopping condition varies (model number, stellar age, a central
  abundance, luminosity, …), so there's no reliable denominator. `mesa_run_status` reports
  models-written + the log tail (concrete progress) rather than a percentage. Revisit later.
