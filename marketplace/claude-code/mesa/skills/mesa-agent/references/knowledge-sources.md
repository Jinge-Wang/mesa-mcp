# Knowledge sources — where to find things

Always prefer these **local, version-correct** sources over memory. They read `$MESA_DIR` first
(the install's `.defaults` files and `docs/source/*.rst`) and fall back to `docs.mesastar.org` for
the matching version only when local files are absent.

## Verifying controls (do this before writing any inlist)

| Need | Tool |
|---|---|
| A control's **exact default + documentation** | `mesa_docs_option('<name>')` — authoritative, parsed from the `.defaults` files (controls, star_job, pgstar, eos, kap, binary, astero). Optionally pass a `namelist`. |
| A control/concept by **keyword** (discovery) | `mesa_docs_search(query)` — ranked across the docs **and** every option; then `mesa_docs_page(path)` to read a hit in full |
| An **output column**'s meaning + whether it's default-selected | `mesa_data_column('<name>', kind='history' or 'profile')` — from the master `*_columns.list` |

## Documentation

| Need | Tool / page |
|---|---|
| Any doc page in full | `mesa_docs_page('<path or URL>')` |
| **Known bugs** for the active version | `mesa_docs_page('known_bugs')` |
| How to run / output / build inlists / PGSTAR / extend / best practices / troubleshoot | `mesa_docs_page('using_mesa/running' | 'using_mesa/output' | 'using_mesa/building_inlists' | 'using_mesa/using_pgstar' | 'using_mesa/extending_mesa' | 'using_mesa/best_practices' | 'using_mesa/troubleshooting')` |
| Inlist/namelist format, run_star_extras hooks, env vars | `mesa_docs_page('reference/format' | 'reference/hooks' | 'reference/env_vars')` |
| Getting started / installing | `mesa_docs_page('quickstart' | 'installation')` |
| Module list / overviews | `mesa_docs_page('modules')`, `'<module>/overview'` |
| Developing MESA (code_style, tour, debugging, …) | `mesa_docs_page('developing')`, `'developing/<topic>'` |
| A verified example setup + its **real inlists** | `mesa_docs_testsuite()` → `mesa_docs_testsuite(name)` |
| MESA Fortran source symbol search | `shmesa grep <string>` via `mesa_env_shell` (optional, best-effort) |
| Build/Fortran-style notes (when present) | read `$MESA_DIR/CLAUDE.md` if it exists |

## Community & literature

| Need | Tool |
|---|---|
| Published, shared inlists to learn from | `mesa_find_search(query)` → `mesa_find_download(<index or title>)` (downloaded to an ephemeral session dir) |
| Papers that used MESA | `mesa_find_search(query)` (Zenodo `mesa` community) |
| Software, datasets, or the **inlists used for a specific paper** | `mesa_find_search(query[, resource_type])` — all Zenodo record types, with per-file download links |
| Community **add-ons** (tools, repos, extensions) | `mesa_find_search(query)` |
| Nuclear reaction rates / data libraries | `mesa_data_rate(reaction, t9)`; `mesa_data_library` → `mesa_data_library(library, name)` |
| Browse the docs in a **browser** | `mesa_docs_serve()` serves the local docs over HTTP (pass `rebuild=True` to build HTML); `mesa_docs_serve()` stops it. Prefer `mesa_docs_search`/`mesa_docs_page` for quick lookups. |

## Rule
If a fact isn't confirmable from these sources for the installed version, say so — don't fill the
gap from memory. Controls and behavior change between MESA versions; `mesa_docs_option` reflects the
*installed* version exactly.
