# Workflow: modify an existing setup and run

Goal: change an existing run safely and re-execute, without corrupting the working setup or the
MESA install.

## Steps

1. **Read before you write.** Open the target `inlist*` (and `src/run_star_extras.f90` if relevant)
   and understand the current configuration. Never edit a file you haven't read.
2. **Locate the right control.** Confirm the exact control name, namelist, and value format with
   `mesa_search_docs` / `mesa_fetch_doc_page` for the installed version. Controls live in specific
   namelists (`&star_job`, `&controls`, `&kap`, `&eos`, `&pgstar`).
3. **Patch precisely.** Edit only the intended lines; preserve indentation, comments, the `&`/`/`
   structure, and `d`-exponent literals (`references/inlist-namelist-rules.md`). If a parameter is
   commented out, uncomment the specific line rather than adding a duplicate.
4. **Recompile only if needed.** Inlist-only changes do **not** require `./mk`. Recompile
   (`mesa_execute_shell("./mk", "<work dir>")`) only after editing `src/*.f90`.
5. **Run or restart — only with explicit user consent.** Confirm first, then start it **detached**
   (non-blocking) with `mesa_run(<work dir>)` for a fresh run, or `mesa_run(<work dir>, "./re")` to
   resume from the last photo. Monitor with `mesa_run_status`; `mesa_stop_run` cancels.
6. **Verify the change took effect.** Check the terminal output / early `history.data` rows for the
   expected behavior (e.g. the new stopping condition or mass).

## Guardrails
- All edits and runs happen in the sibling work folder, never inside `$MESA_DIR`.
- If the run fails, relay the real error (don't paper over it) and check `known bugs` for the version.
- Keep a copy of a known-good inlist before large edits so changes are reversible.
