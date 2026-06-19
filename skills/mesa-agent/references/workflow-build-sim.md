# Workflow: build a simulation from a verified baseline

Goal: stand up a new, runnable MESA setup by starting from a test-suite case (verified physics +
real inlists) and adapting it — never from a blank file or from memory.

## Steps

1. **Confirm the toolchain.** Call `mesa_get_info`. Note the MESA version, `MESA_DIR`, docs source,
   and core count. If the environment status is INVALID, stop and surface the issues.
2. **Pick a baseline.** Call `mesa_fetch_test_suite_index` and choose the closest case to the user's
   goal (e.g. `1M_pre_ms_to_wd`, `1.5M_with_diffusion`, `make_zams`, a `binary/` case for systems).
3. **Study it.** Call `mesa_fetch_test_suite_details(<name>)` to read the description and the real
   `inlist_*` files. This is the configuration you adapt.
4. **Provision a work folder — after confirming the location.** Propose the target directory and
   **get the user's confirmation** (offer a custom path); never create it silently. Then call
   `mesa_create_workspace(name, baseline)` — `baseline` is the chosen test-suite case (replicate it
   with its real inlists) or `'work'` / `'binary'` for a clean template. It copies OUTSIDE `$MESA_DIR`.
5. **Adapt the inlists by patching, not rewriting.** Use `mesa_set_inlist_option` for each change.
   Set only what the goal requires (mass, metallicity, stopping condition, the specific physics).
   **For anything the user didn't specify, don't guess silently:** reason about it, propose a value
   with your reasoning, and ask the user to confirm before writing it. Add **only relevant** controls
   — leave everything else at its default. Verify names/defaults with `mesa_get_option`. Keep `Zbase`
   (`&kap`) and `initial_z` (`&controls`) consistent. Follow `references/inlist-namelist-rules.md`.
6. **Review the configuration.** Call `mesa_show_inlist_settings(<work dir>)` and confirm the set
   options (and that nothing unknown/irrelevant slipped in) with the user before running.
7. **Set parallelism + compile.** `mesa_set_openmp_threads(<cores>)`, then `mesa_execute_shell("./mk",
   "<work dir>")` (or `make`). Relay compiler errors.
8. **Run — only with explicit user consent.** State the command and workspace and **wait for the
   user to confirm**, then start it **detached** with `mesa_run(<work dir>)` — non-blocking, so it
   won't hang the session even for a long or non-converging run. Follow progress with
   `mesa_run_status(<work dir>)` (state, models written, last output); `mesa_run_stop` cancels.
9. **Inspect output.** Use `mesa_read_history(<work dir>, columns=…, last_n=…)` for a sliced,
   downsampled view — never dump whole tables (`mesa_get_output_column` documents any column). For
   **plots**, enable PGSTAR file output (`mesa_enable_pgstar_file_output`) *before* running, then view
   with `mesa_latest_plot` — the on-screen window won't open in VS Code (see `references/visualization.md`).

## Guardrails
- Check `known bugs` (via `mesa_search_docs`) for the active version before relying on a feature.
- If a control you expect is missing, it may be version-specific — confirm via docs, don't guess.
