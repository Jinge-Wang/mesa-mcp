# Workflow: build a simulation from a verified baseline

Goal: stand up a new, runnable MESA setup by starting from a test-suite case (verified physics +
real inlists) and adapting it — never from a blank file or from memory.

## Steps

1. **Confirm the toolchain.** Call `get_mesa_info`. Note the MESA version, `MESA_DIR`, docs source,
   and core count. If the environment status is INVALID, stop and surface the issues.
2. **Pick a baseline.** Call `mesa_fetch_test_suite_index` and choose the closest case to the user's
   goal (e.g. `1M_pre_ms_to_wd`, `1.5M_with_diffusion`, `make_zams`, a `binary/` case for systems).
3. **Study it.** Call `mesa_fetch_test_suite_details(<name>)` to read the description and the real
   `inlist_*` files. This is the configuration you adapt.
4. **Provision a work folder** with `mesa_create_workspace(name, baseline)`. `baseline` is the
   chosen test-suite case (to replicate it with its real inlists), or `'work'` / `'binary'` for a
   clean template. It copies to a folder OUTSIDE `$MESA_DIR` (run outputs excluded) and returns the
   path + inlists. Never build inside `$MESA_DIR`. (`mesa_list_workspaces` shows existing ones.)
5. **Adapt the inlists by patching, not rewriting.** Change only what the goal requires (mass,
   metallicity, stopping condition, physics flags). **Verify every control** with `mesa_search_docs`
   before writing it. Keep `Zbase` (`&kap`) and `initial_z` (`&controls`) consistent. Follow
   `references/inlist-namelist-rules.md`.
6. **Set parallelism.** `set_openmp_threads(<cores from get_mesa_info>)`.
7. **Compile.** `mesa_execute_shell("./mk", "<work dir>")`. Relay any compiler errors.
8. **Run — only with user consent.** Confirm, then `mesa_execute_shell("./rn", "<work dir>")`.
   Runs can be long; this call is bounded, so for long evolutions tell the user and prefer a
   detached run when that capability lands.
9. **Inspect output.** Use `mesa_read_history(<work dir>, columns=…, last_n=…)` for a sliced,
   downsampled view — never dump whole tables. `mesa_get_output_column` documents any column.

## Guardrails
- Check `known bugs` (via `mesa_search_docs`) for the active version before relying on a feature.
- If a control you expect is missing, it may be version-specific — confirm via docs, don't guess.
