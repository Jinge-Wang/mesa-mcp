# Implementation Phase Tracker

See [README.md](README.md) and `agent_context/architecture.md` for detail.

| Phase | Core functional targets | Est. hours | Status |
| :--- | :--- | :--- | :--- |
| **Phase 0** | Design consolidation; revise guideline markdowns; `agent_context/` dev primer + root `AGENTS.md`. | 1–2 | ✅ Complete |
| **Phase 1** | Modular package; version/docs resolver; `mesa_search_docs` (ranked) + `mesa_fetch_doc_page`; `mesa_fetch_test_suite_index`/`details`; `mesa_execute_shell`; refactor info tools; runtime `mesa-agent` skill; basic Claude plugin + platform stubs + `install.sh`. | 6–8 | ✅ Complete |
| **Phase 2** | Web knowledge — done: `mesa_search_community_inlists` + `mesa_download_community_inlist` (session-purge) ✅, `mesa_search_publications` (Zenodo community API) ✅, `mesa_clear_downloads` ✅. Remaining: marketplace add-ons, optional `mesa_serve_docs`. (`known_bugs`/`developing` are already served by `mesa_fetch_doc_page`.) | 4–6 | 🔄 Core done |
| **Reference layer** | `mesa_get_option` + per-option search from the authoritative `*.defaults` files (controls/star_job/pgstar/eos/kap/binary/astero, ~2000 options). | 2–3 | ✅ Complete |
| **Phase 3** | Workspace orchestration: `mesa_create_workspace` (from a test-suite case, or the star/binary template) + `mesa_list_workspaces`, provisioned outside `$MESA_DIR` with run outputs excluded. Coupled multi-run orchestration deferred to Phase 5. | 6–8 | ✅ Core done |
| **Phase 4** | `mesa_set_inlist_option` (format-preserving patcher: update/uncomment/insert, backed up, sandboxed, validated against the option reference) + telemetry: `mesa_get_output_column` (master `*_columns.list`) and `mesa_read_history` (sliced/downsampled, pure stdlib — no pandas). | 4–5 | ✅ Complete |
| **Phase 5** | Async/PID-tracked long runs (`./rn`/`./re`) + monitoring; end-to-end validation. | 3–4 | ⬜ Not started |
