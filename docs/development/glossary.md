# Glossary — MESA domain vocabulary

Just enough MESA terminology to read the code, docs, and test cases. For depth, use
`mesa_search_docs` / the local `$MESA_DIR/docs/source/`.

## Install & environment

- **MESA** — Modules for Experiments in Stellar Astrophysics; a 1D stellar-evolution code suite (Fortran).
- **`MESA_DIR`** — env var pointing at the active MESA install root. Set by `load_mesa`.
- **MESA SDK / `MESASDK_ROOT`** — the prebuilt toolchain (gfortran, libraries) MESA builds against.
- **`load_mesa`** — user shell function that exports `MESA_DIR` and adds tools (incl. `shmesa`) to PATH.
- **`shmesa`** — bash helper script (`$MESA_DIR/scripts/shmesa`). Optional, known-buggy here.
- **`OMP_NUM_THREADS`** — OpenMP thread count controlling MESA's parallelism.

## Modules (top-level MESA dirs)

- **`star`** — the main stellar-evolution engine. **`binary`** — binary-system evolution.
- **`eos`** (equation of state), **`kap`** (opacities), **`net`** (nuclear reaction networks),
  **`rates`**, **`chem`**, **`atm`** (atmospheres), **`astero`** (asteroseismology), **`gyre`**
  (oscillations), **`const`**, **`data`** (physics tables + `version_number`).

## A work directory & running

- **work directory** — a copy of `star/work` (or a test case) where a simulation is set up and run,
  created **outside** the MESA tree.
- **`./mk`** — compile the work directory. **`./rn`** — run. **`./re`** — restart from a photo.
  **`./clean`** — remove build artifacts. **`./rn1`** — run one phase of a multi-part test.
- **`do_one`** — function in `test_suite_helpers` that drives multi-part test runs.

## Inputs (the things we read/patch)

- **inlist** — a Fortran *namelist* config file. Sections: **`&star_job`** (one-time setup),
  **`&eos`**, **`&kap`** (e.g. `Zbase`, opacity tables), **`&controls`** (the physics/run controls,
  e.g. `initial_mass`, `initial_z`), **`&pgstar`** (plots). Each section ends with `/`.
  Values: `.true.`/`.false.`; doubles like `0.02d0`; strings in single quotes; 3-space indent.
- **`run_star_extras.f90`** — user Fortran hooks compiled into a run (`src/run_star_extras.f90`).
- **`history_columns.list` / `profile_columns.list`** — select which quantities are written to output
  (the lever for context-efficient telemetry slicing).
- **`Zbase`** — base metallicity for opacity tables (set in `&kap`). **`initial_z`** — initial metal
  mass fraction (set in `&controls`).

## Outputs

- **`LOGS/`** — output directory. **`history.data`** — one row per saved model (time series).
- **`profile*.data`** — full stellar structure at a saved step. **`photos/`** — binary restart
  checkpoints; **`restart_photo`** — the one `./re` resumes from. **`*.mod`** — saved stellar models.

## Test suite

- **test_suite** — curated, verified example setups (`star/test_suite/`, `binary/test_suite/`) used
  as baselines and regression tests. Each case documents a `required_termination_code_string`
  (its expected stopping condition).
- **`list_tests` / `do1_test_source`** — local enumerations of all test cases.
