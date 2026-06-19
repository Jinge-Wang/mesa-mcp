# MESA MCP Automation Server

An intelligent, physics-aware automation layer built on the [Model Context Protocol](https://modelcontextprotocol.io).
It bridges an AI coding assistant (primarily **VS Code + the Claude extension**) and a local
installation of **MESA** (Modules for Experiments in Stellar Astrophysics), so the agent can
discover documentation, replicate verified test-suite setups, reuse the community's shared inlists
and publications, query nuclear rates and data libraries, run MESA's build/run toolchain, and
analyze and plot results — all inside the user's own sourced environment.

> **Status:** Phases 0–13 are complete (39 tools). See the [roadmap](docs/roadmap.md) for the full
> phase history and any remaining ideas.

> **Example sessions:** the server has been driven end-to-end (build + run a star) from Antigravity
> and Gemini CLI; recorded histories are in [docs/examples/](docs/examples/).

## Project goals

1. **Deterministic environment execution** — wrap every compiler (`./mk`) and runtime (`./rn`,
   `./re`) workflow inside the user's sourced MESA toolchain (via `load_mesa`).
2. **Dynamic knowledge fetching** — answer parameter/format questions from the **local docs first**
   (`$MESA_DIR/docs/source/*.rst`), falling back to `docs.mesastar.org`, to eliminate hallucinated
   inlist syntax.
3. **Deep test-suite parsing** — index the test suite and extract real inlist configurations from
   the actual case directories to replicate verified baselines.
4. **Intent-based workspace orchestration** — turn a scientific goal ("evolve a 1.5 M⊙ star with
   diffusion") into provisioned work folders **outside** the read-only MESA tree.
5. **Context-optimized telemetry & analysis** — return filtered, downsampled history slices,
   structured run status, extracted stellar properties, and rendered plots instead of dumping
   sprawling tables into the context window.

## Architecture at a glance

The server stays a small set of **deterministic tools**; the "intelligence" lives in two guidance
layers:

- **[`docs/development/`](docs/development/)** — guides the agent **developing** this server.
- **[`skills/mesa-agent/`](skills/mesa-agent/)** — guides the agent **using** MESA through the server
  at runtime (ships in the Claude plugin).

Key design choices: **local-first docs** (read `.rst` before the network), **version-aware** (probe
`data/version_number`; `r26.4.1` → `/en/26.4.1/`, a git hash → `/en/latest/`), always following the
**live `$MESA_DIR`**. See [docs/infrastructure.md](docs/infrastructure.md).

```text
$MESA_DIR/              MESA installation   (read-only target; version auto-detected)
mesa-mcp/               this repository      (Python FastMCP server)
<your-work-folders>/    simulation work dirs (created OUTSIDE the MESA tree)
```

## Tools

All tools are implemented. They group as follows (paired names share a logic module):

**Environment & diagnostics**
- `get_mesa_info` — MESA paths, version, compiler, OpenMP, docs source, display capability, `load_mesa` status.
- `set_openmp_threads` — set `OMP_NUM_THREADS` for the session.

**Documentation & knowledge**
- `mesa_get_option` — a control's exact default + docs, from the authoritative `.defaults` files.
- `mesa_search_docs` / `mesa_fetch_doc_page` — ranked local-first docs search; fetch a page (local `.rst` or network).
- `mesa_fetch_test_suite_index` / `mesa_fetch_test_suite_details` — list test cases; get a case's description + real inlists.

**Community & Zenodo**
- `mesa_search_community_inlists` / `mesa_download_community_inlist` — find & fetch marketplace inlists (ephemeral).
- `mesa_search_publications` — search the Zenodo MESA publications community.
- `mesa_search_zenodo` — search the MESA community across all record types (software, datasets, paper-linked inlists) with download links.
- `mesa_search_addons` — search the marketplace add-ons (tools, repos, extensions).
- `mesa_clear_downloads` — purge the ephemeral session download dir.

**Workspaces & inlists**
- `mesa_create_workspace` / `mesa_list_workspaces` — provision/list work folders outside the MESA tree from a baseline.
- `mesa_clean_workspace` — confirm-gated reset of a workspace's run output (LOGS/, photos/, plots, run state); never touches inlists/src.
- `mesa_set_inlist_option` — set a control in an inlist, format-preserving + backed up.
- `mesa_show_inlist_settings` — show set options vs MESA defaults (with units).

**Build, run & monitor**
- `mesa_execute_shell` — run a short command in the sourced MESA env (writes sandboxed).
- `mesa_run` / `mesa_run_status` / `mesa_stop_run` — start a run detached (guards a fresh run over existing output), monitor via JSON status (latest model's columns), cancel.

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
- `mesa_list_data_libraries` / `mesa_load_data` — browse `data/` libraries; load networks, solar abundances, isotope properties.

**MESA installation**
- `mesa_installation_plan` — platform-aware plan: latest MESA release + matching SDK (from Zenodo concept DOIs) and step-by-step guidance.
- `mesa_write_load_mesa` — add a `load_mesa` function to the shell rc (confirm-gated, backed up, duplicate-guarded).

## Installation (target: Claude Code / VS Code, macOS & Linux)

Requires [`uv`](https://docs.astral.sh/uv/) and a working local MESA (`load_mesa` defined,
`MESA_DIR` set):

```bash
./install.sh           # verifies uv, syncs deps, smoke-tests, wires up the server
```

Dependencies are added with your review — the installer/agent shows the exact `uv add` command
rather than running it silently. (If MESA itself isn't installed yet, the `mesa_installation_plan`
and `mesa_write_load_mesa` tools walk you through it.)

## Platform support

The MCP server and its tools are identical across hosts; only registration differs.

| Host | Status | Setup |
|---|---|---|
| **Claude Code / VS Code** | ✅ Primary | `./install.sh` (writes the plugin + `.mcp.json`). |
| **Antigravity** | ✅ Supported | Add the ready-made `marketplace/antigravity/mesa/mcp_config.json` to `~/.gemini/config/mcp_config.json`; load `marketplace/mesa-agent.md` as a context file. |
| **Gemini CLI** | ⚠️ Obsolete → use Antigravity | `gemini mcp add mesa uv run --directory <repo> python main.py`. |
| **Cursor / Codex / Copilot CLI** | 🔜 Planned | Stub plugin dirs under `marketplace/` (`TODO.md` markers). |

After registering, reload the client and call `get_mesa_info` to confirm the toolchain. Example
sessions: [docs/examples/](docs/examples/).

## Documentation

- **[docs/](docs/)** — the documentation hub ([docs/README.md](docs/README.md) is the index).
  - [docs/development/](docs/development/) — guidance for agents/contributors developing the server.
  - [docs/infrastructure.md](docs/infrastructure.md) — runtime, package layout, data flow, caching.
  - [docs/roadmap.md](docs/roadmap.md) — the phased implementation tracker.
  - [docs/examples/](docs/examples/) — recorded example sessions.
- **[AGENTS.md](AGENTS.md)** — the start-here entry point for any agent working in this repo.
- **[skills/mesa-agent/](skills/mesa-agent/)** — the runtime skill that ships in the plugin.

## Development

Start with [AGENTS.md](AGENTS.md), then [docs/development/](docs/development/). The non-negotiable
coding guardrails are in [docs/development/rules.md](docs/development/rules.md).
