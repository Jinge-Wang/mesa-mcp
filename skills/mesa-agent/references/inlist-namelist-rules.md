# Inlist (Fortran namelist) rules

MESA inlists are Fortran namelists. Patch them precisely and keep the format intact — a malformed
namelist makes MESA fail at startup.

## Structure

```fortran
&star_job
   ! one-time setup actions
   create_pre_main_sequence_model = .true.
   save_model_filename = 'start.mod'
/ ! end of star_job namelist

&kap
   Zbase = 0.02d0
   use_Type2_opacities = .true.
/ ! end of kap namelist

&controls
   initial_mass = 1.0d0
   initial_z = 0.02d0
   max_model_number = 1000
/ ! end of controls namelist
```

- Sections: `&star_job` (setup), `&eos`, `&kap` (opacities, incl. `Zbase`), `&controls` (the run
  physics/limits), `&pgstar` (plots). Each begins with `&name` and ends with a line containing `/`.
- **Logicals:** `.true.` / `.false.` (Fortran dot form).
- **Doubles:** use a `d` exponent — `1.0d0`, `0.02d0`, `1d-3`. Avoid bare `1.0`.
- **Strings:** single quotes — `'LOGS_MS'`.
- **Comments:** `!` to end of line.
- **Indentation:** match the file (commonly 3 spaces). Don't reflow lines you didn't change.

## Patching discipline

- **Apply the change with `mesa_set_inlist_option(path, name, value)`** — it patches in place
  (preserving indentation and inline comments), backs up to `.bak`, validates the name, and refuses
  to edit files inside `$MESA_DIR`. Edit by hand only when you need something the tool doesn't cover.
- **Verify first.** Confirm the control name, namelist, and default with `mesa_get_option`
  (or `mesa_search_docs`) against the installed version before writing it.
- **Change only the target line(s).** Don't rewrite the whole file or reorder entries.
- **Uncomment in place.** If a control is present but commented (`! initial_mass = ...`), uncomment
  that line rather than adding a second definition (later duplicates override earlier ones — easy to
  get wrong).
- **Keep `Zbase` and `initial_z` consistent** unless the user intends otherwise.
- **Right namelist.** A control only takes effect in its correct section; a `&controls` key placed in
  `&star_job` is silently ignored.

## Common pitfalls

- Bare floats (`1.5`) instead of `1.5d0` can lose precision — use `d` literals.
- A missing closing `/` or a typo'd `&name` aborts the read.
- Setting a metallicity in only one of `Zbase` / `initial_z`.
- Assuming a control exists — names change across versions; verify via docs.
