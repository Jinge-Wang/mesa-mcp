# MESA MCP Automation Server

An intelligent, physics-aware automation layer built on the [Model Context Protocol](https://modelcontextprotocol.io).
It bridges an AI coding assistant (primarily **VS Code + the Claude extension**) and a local
installation of **MESA** (Modules for Experiments in Stellar Astrophysics), so the agent can
discover documentation, replicate verified test-suite setups, reuse the community's shared inlists
and publications, and run MESA's build/run toolchain inside the user's own sourced environment.

> **Status:** Phases 0–10 are complete — docs/knowledge tools, workspace orchestration, inlist
> patching, telemetry, detached runs, headless PGSTAR plotting, community inlists/publications, the
> reliability & safety quick-wins (JSON run-status, run-over-output guard, confirm-gated cleanup),
> and the rates & data-library toolset (REACLIB rate queries, rate-factor scaling, network/abundance/
> isotope loaders). Phases 11–13 (analyzers + plotting, live viz + MESA install toolset,
> knowledge/Zenodo/add-ons expansion) are planned; see [TRACKER.md](TRACKER.md).

> **Examples:** The server has been tested with Gemini CLI (now obsolete) and Antigravity CLI. Both successfully built and run a mesa star simulation. The command line histories are provided here: [Geimini CLI](docs/sample-gemini-cli.html) and [Antigravity CLI](docs/sample-agy-cli.html).

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
5. **Context-optimized telemetry slicing** — configure output via `history_columns.list` and return
   filtered, downsampled slices instead of dumping sprawling tables into the context window.

## Architecture at a glance

The server stays a small set of **deterministic tools**; the "intelligence" lives in two guidance
layers:

- **[`agent_context/`](agent_context/)** — guides the agent **developing** this server.
- **`skills/mesa-agent/`** — guides the agent **using** MESA through the server at runtime (ships in
  the Claude plugin).

Key design choices: **local-first docs** (read `.rst` before the network), **version-aware** (probe
`data/version_number`; `r26.4.1` → `/en/26.4.1/`, a git hash → `/en/latest/`), always following the
**live `$MESA_DIR`**. See [INFRASTRUCTURE.md](INFRASTRUCTURE.md).

## System topology

```text
$MESA_DIR/              MESA installation   (read-only target; version auto-detected)
mesa-mcp/               this repository      (Python FastMCP server)
<your-work-folders>/    simulation work dirs (created OUTSIDE the MESA tree)
```

## Tools

| Tool | Status | Purpose |
|---|---|---|
| `get_mesa_info` | ✅ | Report MESA paths, version, compiler, OpenMP, docs source. |
| `set_openmp_threads` | ✅ | Set `OMP_NUM_THREADS` for the session. |
| `mesa_get_option` | ✅ | A control's exact default + documentation, from the `.defaults` files. |
| `mesa_search_docs` | ✅ | Ranked top-N search over local docs (network fallback). |
| `mesa_fetch_doc_page` | ✅ | Fetch a doc page (local `.rst` → text, or network). |
| `mesa_fetch_test_suite_index` | ✅ | List star/binary/astero test cases. |
| `mesa_fetch_test_suite_details` | ✅ | Description + real inlists for one case. |
| `mesa_create_workspace` / `mesa_list_workspaces` | ✅ | Provision/list work folders outside the MESA tree from a baseline. |
| `mesa_clean_workspace` | ✅ | Confirm-gated reset of a workspace's run output (LOGS/, photos/, png/, run state); never touches inlists/src. |
| `mesa_set_inlist_option` | ✅ | Set a control in an inlist, format-preserving + backed up. |
| `mesa_show_inlist_settings` | ✅ | Show set options vs MESA defaults (with units) for an inlist/workspace. |
| `mesa_get_output_column` / `mesa_read_history` | ✅ | Look up output columns; read a sliced `history.data`. |
| `mesa_execute_shell` | ✅ | Run a short command in the sourced MESA env (writes sandboxed). |
| `mesa_run` / `mesa_run_status` / `mesa_stop_run` | ✅ | Start a run detached (non-blocking; guards a fresh run over existing output), monitor via JSON status (latest model's columns), and cancel. |
| `mesa_enable_pgstar_file_output` / `mesa_latest_plot` / `mesa_list_plots` | ✅ | Enable & view PGSTAR plots headlessly (file output). |
| `mesa_search_community_inlists` / `mesa_download_community_inlist` | ✅ | Find & fetch shared inlists (ephemeral). |
| `mesa_search_publications` | ✅ | Search the Zenodo MESA publications community. |
| `mesa_clear_downloads` | ✅ | Purge the ephemeral session download dir (also auto-purged on exit). |
| `mesa_get_reaction_rate` | ✅ | Look up a reaction's JINA REACLIB fit set(s), citation, and rate evaluated at T9. |
| `mesa_set_rate_factor` | ✅ | Scale a specific reaction's rate (wraps the `special_rate_factor` array syntax). |
| `mesa_list_data_libraries` / `mesa_load_data` | ✅ | Browse `data/` libraries; load networks, solar abundances, isotope properties. |

## Installation (target: Claude Code / VS Code, macOS & Linux)

Requires [`uv`](https://docs.astral.sh/uv/) and a working local MESA (`load_mesa` defined,
`MESA_DIR` set):

```bash
./install.sh           # verifies uv, syncs deps, smoke-tests, wires up the server
```

Dependencies are added with your review — the installer/agent will show the exact `uv add` command
rather than running it silently.

**Other hosts** (Antigravity, Gemini CLI, …): see [PLATFORMS.md](PLATFORMS.md) for the support
matrix and per-host setup. (Gemini CLI is obsolete → use Antigravity.)

## Development

Start with [AGENTS.md](AGENTS.md), then [`agent_context/`](agent_context/). Coding guardrails live
in [`agent_context/rules.md`](agent_context/rules.md) (summarized in [CODING_RULES.md](CODING_RULES.md)).
