# MESA MCP Automation Server

An intelligent, physics-aware automation layer built on the [Model Context Protocol](https://modelcontextprotocol.io).
It bridges an AI coding assistant and a local installation of **MESA** ([Modules for Experiments in Stellar Astrophysics](https://mesastar.org)), so the agent can discover documentation, replicate verified test-suite setups, reuse the community's shared inlists and publications, query nuclear rates and data libraries, run MESA's build/run toolchain, and analyze and plot results — all inside the user's own sourced environment.

> **Status:** See the [roadmap](docs/roadmap.md) for the full implementation history and any remaining ideas.

> **Example sessions:** the server has been driven end-to-end (build + run a star) from Antigravity and Gemini CLI; recorded histories are in [docs/examples/](docs/examples/).

## Platform support

The MCP server and its tools are identical across hosts; only registration differs.

| Host | Status | Setup |
|---|---|---|
| **Claude Code / VS Code** | ✅ Primary | `./install.sh` (writes the plugin + `.mcp.json`). |
| **Antigravity** | ✅ Supported | Add the ready-made `marketplace/antigravity/mesa/mcp_config.json` to `~/.gemini/config/mcp_config.json`; load `marketplace/mesa-agent.md` as a context file. |
| **Gemini CLI** | ⚠️ Obsolete → use Antigravity | `gemini mcp add mesa uv run --directory <repo> python main.py`. |
| **Cursor / Codex / Copilot CLI** | 🔜 Planned | Stub plugin dirs under `marketplace/` (`TODO.md` markers). |

After registering, reload the client and call `mesa_get_info` to confirm the toolchain. Example
sessions: [docs/examples/](docs/examples/).

## Project goals

1. **Deterministic environment execution** — wrap every compiler (`./mk`) and runtime (`./rn`, `./re`) workflow inside the user's sourced MESA toolchain (via `load_mesa`).
2. **Dynamic knowledge fetching** — answer parameter/format questions from the **local docs first** (`$MESA_DIR/docs/source/*.rst`), falling back to `docs.mesastar.org`, to eliminate hallucinated inlist syntax.
3. **Deep test-suite parsing** — index the test suite and extract real inlist configurations from the actual case directories to replicate verified baselines.
4. **Intent-based workspace orchestration** — turn a scientific goal ("evolve a 1.5 M⊙ star with diffusion") into provisioned work folders **outside** the read-only MESA tree.
5. **Context-optimized telemetry & analysis** — return filtered, downsampled history slices, structured run status, extracted stellar properties, and rendered plots instead of dumping sprawling tables into the context window.

## Installation (target: Claude Code / VS Code, macOS & Linux)

Requires [`uv`](https://docs.astral.sh/uv/) and a working local MESA (`MESA_DIR` set; [`load_mesa`](#load-mesa-note) defined preferably):

```bash
./install.sh           # verifies uv, syncs deps, smoke-tests, wires up the server
```

Dependencies are added after user review — the installer/agent shows the exact `uv add` command rather than running it silently. (If MESA itself isn't installed yet, the `mesa_install_plan` and `mesa_install_set_env` tools walk user through it.)

<a id="load-mesa-note"></a>
> [!NOTE]
> `load_mesa` is not a standard function shipped with MESA. It must be added manually to user's shell configuration file (`~/.bashrc` or `~/.zshrc`) after installing the MESA SDK and downloading the MESA source code.
> While optional, running MESA inside this function provides an isolated environment and prevents MESA variables from overwriting user's existing system settings.
>
> * **Important:** Remember to replace the placeholder absolute paths below with your actual local installation paths (for example, macOS users typically have `MESASDK_ROOT` located in the `/Applications/mesasdk` folder).
>
> ```bash
> function load_mesa() {
>     # 1. Define Directories
>     export MESA_DIR=/absolute/path/to/mesa
>     export MESASDK_ROOT=/absolute/path/to/mesasdk
> 
>     # 2. Initialize the SDK
>     source \$MESASDK_ROOT/bin/mesasdk_init.sh
> 
>     # 3. Set MESA-specific environment variables
>     export OMP_NUM_THREADS=14
>     export PATH=PATH:MESA_DIR/scripts/shmesa
> 
>     # 4. Update the visual prompt tag
>     export PS1="(mesa) \$PS1"
> 
>     echo "MESA SDK and Environment successfully loaded for this session!"
> }
> ```

## Architecture at a glance

The server stays a small set of **deterministic tools**; the "intelligence" lives in two guidance layers:

- **[`docs/development/`](docs/development/)** — guides the agent **developing** this server.
- **[`skills/mesa-agent/`](skills/mesa-agent/)** — guides the agent **using** MESA through the server at runtime (ships in the Claude plugin).

Key design choices: **local-first docs** (read `.rst` before the network), **version-aware** (probe `data/version_number`; `r26.4.1` → `/en/26.4.1/`, a git hash → `/en/latest/`), always following the **live `$MESA_DIR`**. See [docs/infrastructure.md](docs/infrastructure.md).

```text
$MESA_DIR/              MESA installation   (read-only target; version auto-detected)
mesa-mcp/               this repository      (Python FastMCP server)
<your-work-folders>/    simulation work dirs (created OUTSIDE the MESA tree)
```

## Tools

Tools group as follows (paired names share a logic module):

**Environment & diagnostics**
- `mesa_get_info` — MESA paths, version, compiler, OpenMP, docs source, display capability, `load_mesa` status.
- `mesa_set_openmp_threads` — set `OMP_NUM_THREADS` for the session.

**Documentation & knowledge**
- `mesa_get_option` — a control's exact default + docs, from the authoritative `.defaults` files.
- `mesa_search_docs` / `mesa_fetch_doc_page` — ranked local-first docs search; fetch a page (local `.rst` or network).
- `mesa_serve_docs` / `mesa_stop_docs` — serve the local docs as a website (detached; optional `sphinx-build`).
- `mesa_fetch_test_suite_index` / `mesa_fetch_test_suite_details` — list test cases; get a case's description + real inlists.

**Community & Zenodo**
- `mesa_search_community_inlists` / `mesa_download_community_inlist` — find & fetch marketplace inlists (ephemeral).
- `mesa_search_publications` — search the Zenodo MESA publications community.
- `mesa_search_zenodo` — search the MESA community across all record types (software, datasets, paper-linked inlists) with download links.
- `mesa_search_addons` — search the marketplace add-ons (tools, repos, extensions).
- `mesa_clear_downloads` — purge the ephemeral session download dir.

**Workspaces & inlists**
- `mesa_create_workspace` / `mesa_list_workspaces` — provision/list work folders outside the MESA tree from a baseline.
- `mesa_clear_workspace` — confirm-gated reset of a workspace's run output (LOGS/, photos/, plots, run state); never touches inlists/src.
- `mesa_set_inlist_option` — set a control in an inlist, format-preserving + backed up.
- `mesa_show_inlist_settings` — show set options vs MESA defaults (with units).

**Build, run & monitor**
- `mesa_execute_shell` — run a short command in the sourced MESA env (writes sandboxed).
- `mesa_run` / `mesa_run_status` / `mesa_run_stop` — start a run detached (guards a fresh run over existing output), monitor via JSON status (latest model's columns), cancel.

**Telemetry, analysis & plotting**
- `mesa_get_output_column` / `mesa_read_history` — look up output columns; read a sliced `history.data`.
- `mesa_analyze_history` / `mesa_analyze_profile` — extract core masses, central abundances, evolutionary phase, convective zones, burning regions.
- `mesa_plot_history` / `mesa_plot_profile` — render plots (matplotlib → inline PNG); presets `hr`, `kippenhahn`, `abundance`.

**Visualization (PGSTAR & live view)**
- `mesa_enable_pgstar_file_output` / `mesa_latest_plot` / `mesa_list_plots` — enable & view PGSTAR plots headlessly (file output).
- `mesa_open_live_view` / `mesa_close_live_view` — open a separate auto-refreshing desktop window that follows a run's newest plot (where a display exists).

**Nuclear rates & data libraries**
- `mesa_get_reaction_rate` — a reaction's JINA REACLIB fit set(s), citation, and rate evaluated at T9.
- `mesa_set_rate_factor` — scale a specific reaction's rate (wraps the `special_rate_factor` array syntax).
- `mesa_list_data_libraries` / `mesa_load_data` — browse `data/` libraries; parse networks, solar abundances, isotopes, and `colors` filters/models; structured inventory for the rest.

**MESA installation**
- `mesa_install_plan` — platform-aware plan: latest MESA release + matching SDK (from Zenodo concept DOIs) and step-by-step guidance.
- `mesa_install_set_env` — add a `load_mesa` function to the shell rc (confirm-gated, backed up, duplicate-guarded).

## Support & limitations

The server is built and tested primarily around **single-star evolution**. Coverage of the wider MESA
ecosystem is uneven — treat the "partial" and "not yet" rows as **not fully tested**:

| Area | Status |
|---|---|
| **Single-star (`star`)** — diagnostics, docs/option lookup, test-suite replication, workspaces, inlist editing, run + monitor, telemetry/analysis/plotting | ✅ Supported & exercised |
| **Nuclear rates (`net`/REACLIB)** and the **network / Lodders-abundance / isotope** data libraries | ✅ Supported |
| **`binary`** — workspace template + `&binary_controls` options | ⚠️ Partial (less end-to-end testing) |
| **`astero`** — `&astero_search_controls` options via the reference layer | ⚠️ Partial (no asteroseismic post-processing) |
| **`colors`** — filter sets (by survey) + stellar-model grids via `mesa_load_data` | ⚠️ Parsed/inventoried (no magnitude pipeline yet) |
| **Other `data/` libraries** (`atm`, `eos`, `kap`, `ionization`, `roche`) | ⚠️ Structured inventory via `mesa_load_data`, not numerically parsed |
| **GYRE / adipls** (stellar oscillations / asteroseismology) | ⚠️ Detected/reported by `mesa_get_info`, not driven |
| **Platform** | macOS (Apple Silicon) tested; Linux supported by design but less exercised; Windows unsupported |

Broadening this coverage is tracked as **Phase 14** in the [roadmap](docs/roadmap.md).

## Documentation

- **[docs/](docs/)** — the documentation hub ([docs/README.md](docs/README.md) is the index).
  - [docs/development/](docs/development/) — guidance for agents/contributors developing the server.
  - [docs/infrastructure.md](docs/infrastructure.md) — runtime, package layout, data flow, caching.
  - [docs/roadmap.md](docs/roadmap.md) — the phased implementation tracker.
  - [docs/examples/](docs/examples/) — recorded example sessions.
- **[AGENTS.md](AGENTS.md)** — the start-here entry point for any agent working in this repo.
- **[skills/mesa-agent/](skills/mesa-agent/)** — the runtime skill that ships in the plugin.

## Development

Start with [AGENTS.md](AGENTS.md), then [docs/development/](docs/development/). The non-negotiable coding guardrails are in [docs/development/rules.md](docs/development/rules.md).
