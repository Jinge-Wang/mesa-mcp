# Knowledge sources — where to find things

Always prefer these **local, version-correct** sources over memory. They read `$MESA_DIR` first
(the install's `.defaults` files and `docs/source/*.rst`) and fall back to `docs.mesastar.org` for
the matching version only when local files are absent.

## Verifying controls (do this before writing any inlist)

| Need | Tool |
|---|---|
| A control's **exact default + documentation** | `mesa_get_option('<name>')` — authoritative, parsed from the `.defaults` files (controls, star_job, pgstar, eos, kap, binary, astero). Optionally pass a `namelist`. |
| A control/concept by **keyword** (discovery) | `mesa_search_docs(query)` — ranked across the docs **and** every option; then `mesa_fetch_doc_page(path)` to read a hit in full |
| An **output column**'s meaning + whether it's default-selected | `mesa_get_output_column('<name>', kind='history' or 'profile')` — from the master `*_columns.list` |

## Documentation

| Need | Tool / page |
|---|---|
| Any doc page in full | `mesa_fetch_doc_page('<path or URL>')` |
| **Known bugs** for the active version | `mesa_fetch_doc_page('known_bugs')` |
| How to run / output / build inlists / PGSTAR / extend / best practices / troubleshoot | `mesa_fetch_doc_page('using_mesa/running' | 'using_mesa/output' | 'using_mesa/building_inlists' | 'using_mesa/using_pgstar' | 'using_mesa/extending_mesa' | 'using_mesa/best_practices' | 'using_mesa/troubleshooting')` |
| Inlist/namelist format, run_star_extras hooks, env vars | `mesa_fetch_doc_page('reference/format' | 'reference/hooks' | 'reference/env_vars')` |
| Getting started / installing | `mesa_fetch_doc_page('quickstart' | 'installation')` |
| Module list / overviews | `mesa_fetch_doc_page('modules')`, `'<module>/overview'` |
| Developing MESA (code_style, tour, debugging, …) | `mesa_fetch_doc_page('developing')`, `'developing/<topic>'` |
| A verified example setup + its **real inlists** | `mesa_fetch_test_suite_index()` → `mesa_fetch_test_suite_details(name)` |
| MESA Fortran source symbol search | `shmesa grep <string>` via `mesa_execute_shell` (optional, best-effort) |
| Build/Fortran-style notes (when present) | read `$MESA_DIR/CLAUDE.md` if it exists |

## Community & literature

| Need | Tool |
|---|---|
| Published, shared inlists to learn from | `mesa_search_community_inlists(query)` → `mesa_download_community_inlist(<index or title>)` (downloaded to an ephemeral session dir) |
| Papers that used MESA | `mesa_search_publications(query)` (Zenodo `mesa` community) |
| Software, datasets, or the **inlists used for a specific paper** | `mesa_search_zenodo(query[, resource_type])` — all Zenodo record types, with per-file download links |
| Community **add-ons** (tools, repos, extensions) | `mesa_search_addons(query)` |
| Nuclear reaction rates / data libraries | `mesa_get_reaction_rate(reaction, t9)`; `mesa_list_data_libraries` → `mesa_load_data(library, name)` |
| Browse the docs in a **browser** | `mesa_serve_docs()` serves the local docs over HTTP (pass `rebuild=True` to build HTML); `mesa_stop_docs()` stops it. Prefer `mesa_search_docs`/`mesa_fetch_doc_page` for quick lookups. |

## Rule
If a fact isn't confirmable from these sources for the installed version, say so — don't fill the
gap from memory. Controls and behavior change between MESA versions; `mesa_get_option` reflects the
*installed* version exactly.
