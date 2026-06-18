# Assumptions — environment facts the server relies on

These were verified during project kickoff. Trust them, but re-check a specific path or function
before depending on it — the active install gets re-pointed and versions change.

## The active MESA install

- The user's MESA installation is whatever `$MESA_DIR` points at. **Always follow the live
  `$MESA_DIR`** — never hard-code an install path. Treat the MESA tree as **read-only**.
- `MESA_DIR` is typically set by a `load_mesa` shell function (and that function also adds
  `$MESA_DIR/scripts/shmesa` to `PATH`). It is usually **empty in the inherited process
  environment**, so the server sources the user's shell profile and runs `load_mesa` to populate it
  — handled by the `environment.py` helpers (`source_shell_environment`, `build_env_context`).

## Version → docs mapping

- `$MESA_DIR/data/version_number` contains either a **release string** (e.g. `r26.4.1`, from an
  official download) or a **git commit hash** (e.g. `f12c70cf`, from a source checkout).
- Rule: matches `^r?\d+\.\d+(\.\d+)?$` → release; use that number for the docs URL
  (`https://docs.mesastar.org/en/<version>/`). Otherwise → use `latest`.
- The `MESA_DOCS_VERSION` env var overrides the detected value.

## Documentation

- A MESA install ships a **Sphinx source tree** at `$MESA_DIR/docs/source/` (~300+ `.rst` files,
  tens of MB): `known_bugs.rst`, `developing/`, `test_suite.rst` + `test_suite/`, `reference/`,
  `faq.rst`, and module overviews (`kap/`, `eos/`, `net/`, `rates/`, `atm/`, …).
- **There is NO prebuilt HTML and NO `searchindex.js`** locally — only `.rst` source. Local search
  means indexing the `.rst`. Rendering to HTML would require `sphinx-build` (deferred).
- Source checkouts may also carry a top-level `CLAUDE.md` (build/test/Fortran-style notes); official
  downloads do not. Treat it as an optional local knowledge source when present.

## What is JS-rendered (must use local files or APIs, never HTML scraping)

- **Sphinx docs search** (`docs.mesastar.org/.../search.html?q=`) runs client-side via
  `searchindex.js`. A plain HTTP GET returns an empty shell.
- **Zenodo records page** (`zenodo.org/communities/mesa/records?...`) is a React app — same trap.
  Use the REST API: `https://zenodo.org/api/records?communities=mesa&q=<query>` →
  `hits.hits[].metadata.{title,creators[].name,doi,publication_date}` + `links.self_html`.
- **Community inlists** (`mesastar.org/marketplace/inlists/`) IS a static 5-column HTML table
  (Author, Title, Paper Link→adsabs, MESA version, Download→Zenodo DOI), ~250 rows — safe to scrape.

## shmesa (optional, known-buggy)

`$MESA_DIR/scripts/shmesa/shmesa` provides bash subcommands: `work`, `change`, `defaults`, `cp`,
`grep`, `extras`, `zip`, `version`, `help`. **It has known bugs**, so never make a tool depend on it.
Its `grep` (search MESA source) is a handy convenience. Note: `shmesa change` backs up to `.bak` but
normalizes indentation to 4 spaces and drops inline comments — which is why our inlist patcher
(Phase 4) is first-party.

## Python toolchain

- The project runs on Python **3.12**, managed by **`uv`** (`uv.lock`, `.python-version`);
  `pyproject.toml` requires `>=3.12`.
- Runtime deps: `mcp` (FastMCP), `httpx`, `beautifulsoup4`. `httpx`/`beautifulsoup4` are imported
  lazily so the local-first core works even before they are installed.
- Adding dependencies requires explicit user approval (see `rules.md`).

## Test suite (ground truth for the parsers)

- `$MESA_DIR/star/test_suite/` (~90+ cases) and `$MESA_DIR/binary/test_suite/` (a handful);
  `astero/test_suite/` also exists. Local index helpers: `list_tests`, `do1_test_source`,
  `test_suite_helpers` (defines `do_one`).
- A case dir contains: `inlist_*` namelists, `rn`/`rn1`/`re`/`ck` scripts, `src/run_star_extras.f90`,
  `history_columns.list`, `profile_columns.list`, `README.rst`.
- Inlist format = Fortran namelists: `&star_job` / `&eos` / `&kap` / `&controls` / `&pgstar`, each
  closed by `/ ! end of <name> namelist`; `.true.`/`.false.`; double literals like `0.02d0`; 3-space indent.
