# MESA MCP Automation Server

An intelligent, physics-aware automation layer built on the [Model Context Protocol](https://modelcontextprotocol.io).
It bridges an AI coding assistant and a local installation of **MESA** ([Modules for Experiments in Stellar Astrophysics](https://mesastar.org)), so the agent can discover documentation, replicate verified test-suite setups, reuse the community's shared inlists and publications, query nuclear rates and data libraries, run MESA's build/run toolchain, and analyze and plot results — all inside the user's own sourced environment.

> **Status:** See the [roadmap](docs/roadmap.md) for the full implementation history and remaining ideas.

> **Example sessions:** 
the server has been driven end-to-end (build + run a star) from Antigravity and Gemini CLI; recorded histories are in [docs/examples/](docs/examples/). (The later transcript predates the tool-naming reorganization below.)

The worked [antigravity CLI transcript](docs/examples/sample-antigravity-cli.html) demonstrates the agent successfully working out the simulation settings for the first lab of the MESA Summer School 2026, without any prior knowledge of the curriculum. While this is a relatively naive problem, it highlights the agent's ability to navigate the MESA documentation, configure the workspace, and debug live errors. The agent does require some further improvement regarding domain-specific nuances (for example, initially navigating the a09 opacity tables before being prompted to use the hand-smoothed nans-removed table for the AGSS09 result).

## Tool naming at a glance

Every tool follows `mesa_<area>_<detail>` across **seven areas** — so the right tool is easy to find and the set stays small (30 tools):

| Area | Prefix | What it covers |
|---|---|---|
| Environment & setup | `mesa_env_*` | diagnostics, shell exec, OpenMP threads, MESA install help |
| Documentation & reference | `mesa_docs_*` | docs search/fetch, option reference, test suite, docs server |
| Ecosystem discovery | `mesa_find_*` | community inlists, publications, Zenodo, add-ons, downloads |
| Workspaces & inlists | `mesa_work_*` | create/list/clear work folders, edit/show inlists |
| Execute & monitor | `mesa_run_*` | start/status/stop detached runs, GYRE |
| Read & analyze data | `mesa_data_*` | history slices, columns, analyzers, data libraries, rates |
| Visualization | `mesa_plot_*` | matplotlib plots, PGSTAR/pgbinary output, view, live window |

The full list is in [Tools](#tools).

## Installation (macOS & Linux)

### 0. Install `uv`

This server's Python environment is managed by [`uv`](https://docs.astral.sh/uv/). If you don't have it, follow the **[official installation guide](https://docs.astral.sh/uv/getting-started/installation/)**, e.g.:

```bash
# macOS / Linux (standalone installer)
curl -LsSf https://astral.sh/uv/install.sh | sh
# or, with Homebrew on macOS
brew install uv
```

### 1. Have a working MESA (or let the agent help)

You need a local MESA install with `MESA_DIR` set (a `load_mesa` shell function is the recommended way — see the [note below](#load-mesa-note)). If MESA isn't installed yet, you can install the MCP server first following the next step and aks the AI agent to use the `mesa_env_install` tool (`action="plan"` then `action="set_env"`), which will walk you through downloading the matching MESA + SDK and writing `load_mesa`.

### 2. Run the installer

```bash
./install.sh            # verifies uv, syncs deps, smoke-tests, writes the MCP configs + plugin
```

It checks for `uv`, installs the Python dependencies into `.venv` (after asking), and writes the absolute repo path into the `.mcp.json` files. Dependencies are added only after review — the installer/agent shows the exact command rather than running `uv add` silently.

### 3. Register the server with your host

The MCP server and its 30 tools are identical across hosts; only registration differs.

**Claude extension in VS Code (marketplace install):** 
The VS Code Claude extension does **not** ship the `claude` CLI, so registration is **manual**: open `~/.claude.json` and add the `mesa` block (the installer wrote a ready-made copy to `<repo>/.mcp.json` — copy the inner block into the `mcpServers` object):

```jsonc
// ~/.claude.json
{
  "mcpServers": {
    "mesa": {
      "command": "uv",
      "args": ["run", "--directory", "/ABSOLUTE/PATH/TO/mesa-mcp", "python", "main.py"]
    }
    // ...your other servers...
  }
}
```

Then reload VS Code (Cmd/Ctrl+Shift+P -> "Developer: Reload Window").

**VS Code native MCP / GitHub Copilot:** 
Command Palette -> "MCP: Open User Configuration" and paste the same `mesa` block.

**Claude Code CLI** (only if you have the `claude` command):

```bash
claude plugin marketplace add "/ABSOLUTE/PATH/TO/mesa-mcp/marketplace"
claude plugin install mesa@mesa-mcp
# ...or just the server:
claude mcp add mesa -- uv run --directory "/ABSOLUTE/PATH/TO/mesa-mcp" python main.py
```

**Other hosts** (Antigravity, Gemini CLI, Cline/Roo, …): see the [Platform support](#platform-support) table below; `./install.sh` prints the exact per-host commands at the end. The registration process is similar to Claude Code CLI.

### 4. Confirm it works

Reload the client, then ask the AI: *"Call `mesa_env_info` to confirm the toolchain."*

<a id="load-mesa-note"></a>
> [!NOTE]
> `load_mesa` is not shipped with MESA. Add it to your shell rc (`~/.bashrc` / `~/.zshrc`) after installing the MESA SDK and source code (or let `mesa_env_install action="set_env"` write it for you). Running MESA inside a function keeps its environment isolated from your normal shell.
>
> * **Replace the placeholder paths** with your real install paths (on macOS the SDK is typically `/Applications/mesasdk`).
>
> ```bash
> function load_mesa() {
>     # 1. Directories
>     export MESA_DIR=/absolute/path/to/mesa
>     export MESASDK_ROOT=/absolute/path/to/mesasdk
>
>     # 2. Initialize the SDK
>     source $MESASDK_ROOT/bin/mesasdk_init.sh
>
>     # 3. MESA-specific environment
>     export OMP_NUM_THREADS=14
>     export PATH=$PATH:$MESA_DIR/scripts/shmesa
>
>     # 4. Visual prompt tag
>     export PS1="(mesa) $PS1"
>
>     echo "MESA SDK and environment loaded for this session."
> }
> ```

## Platform support

| Host | Status | Setup |
|---|---|---|
| **Claude extension (VS Code)** | ✅ Supported | `./install.sh`, then add the `mesa` block to `~/.claude.json` (no `claude` CLI from the marketplace extension). |
| **VS Code native MCP / Copilot** | ✅ Supported | "MCP: Open User Configuration" -> paste the `mesa` block from `.mcp.json`. |
| **Claude Code CLI** | ✅ Supported | `claude plugin marketplace add marketplace/` + `claude plugin install mesa@mesa-mcp`, or `claude mcp add`. |
| **Antigravity** | ✅ Supported | Add `marketplace/antigravity/mesa/mcp_config.json` to `~/.gemini/config/mcp_config.json`; load `marketplace/mesa-agent.md` as a context file. |
| **Gemini CLI** | ⚠️ Obsolete -> use Antigravity | `gemini mcp add mesa uv run --directory <repo> python main.py`. |
| **Cursor / Codex / Copilot CLI** | ⚠️ Not tested | The server itself shall be easily registered (not verified though). Stub plugin dirs under `marketplace/` (`TODO.md` markers). |

## Project goals

1. **Deterministic environment execution** — wrap every compiler (`./mk`) and runtime (`./rn`, `./re`) workflow inside the user's sourced MESA toolchain (via `load_mesa`).
2. **Dynamic knowledge fetching** — answer parameter/format questions from the **local docs first** (`$MESA_DIR/docs/source/*.rst`), falling back to `docs.mesastar.org`, to eliminate hallucinated inlist syntax.
3. **Deep test-suite parsing** — index the test suite and extract real inlist configurations from the actual case directories to replicate verified baselines.
4. **Intent-based workspace orchestration** — turn a scientific goal into provisioned work folders **outside** the read-only MESA tree.
5. **Context-optimized telemetry & analysis** — return filtered, downsampled history slices, structured run status, extracted stellar/orbital properties, and rendered plots instead of dumping sprawling tables into the context window.

## Architecture at a glance

The server stays a small set of **deterministic tools**; the "intelligence" lives in two guidance layers:

- **[`docs/development/`](docs/development/)** — guides the agent **developing** this server.
- **[`skills/mesa-agent/`](skills/mesa-agent/)** — guides the agent **using** MESA through the server at runtime (ships in the Claude plugin).

Key design choices: **local-first docs** (read `.rst` before the network), **version-aware** (probe `data/version_number`; `r26.4.1` -> `/en/26.4.1/`, a git hash -> `/en/latest/`), always following the **live `$MESA_DIR`**, and an **inlist-chain resolver** so output paths/filenames are read from the actual inlists (not assumed). See [docs/infrastructure.md](docs/infrastructure.md).

```text
$MESA_DIR/              MESA installation   (read-only target; version auto-detected)
mesa-mcp/               this repository      (Python FastMCP server)
<your-work-folders>/    simulation work dirs (created OUTSIDE the MESA tree)
```

## Tools

30 tools in seven `mesa_<area>_<detail>` families. Tools that fold parallel variants take a `kind`/`action`/`source` argument (still one call — no extra round-trips).

**Environment & setup — `mesa_env_*`**
- `mesa_env_info` — MESA paths, version, compiler, OpenMP, docs source, window capability, GYRE, `load_mesa` status.
- `mesa_env_shell` — run a short command in the sourced MESA env (writes sandboxed outside `$MESA_DIR`).
- `mesa_env_threads` — set `OMP_NUM_THREADS` for the session.
- `mesa_env_install` — `action="plan"` (platform-aware MESA+SDK plan) / `"set_env"` (write a `load_mesa` function, confirm-gated).

**Documentation & reference — `mesa_docs_*`**
- `mesa_docs_option` — a control's exact default + docs, from the authoritative `.defaults` files (controls/star_job/eos/kap/pgstar, **binary_controls/binary_job/pgbinary**, astero).
- `mesa_docs_search` / `mesa_docs_page` — ranked local-first docs search; fetch a page (local `.rst` or network).
- `mesa_docs_testsuite` — list test cases (no arg) or a case's description + real inlists (case name).
- `mesa_docs_serve` — `action="start"|"stop"` a local docs website (optional `sphinx-build`).

**Ecosystem discovery — `mesa_find_*`**
- `mesa_find_search` — `source="inlists"|"publications"|"zenodo"|"addons"|"all"` (community inlists, MESA papers, the whole Zenodo community with downloadable files, marketplace add-ons).
- `mesa_find_download` — fetch a community inlist's files (ephemeral session scratch).
- `mesa_find_clear` — purge the session download dir.

**Workspaces & inlists — `mesa_work_*`**
- `mesa_work_create` / `mesa_work_list` — provision/list work folders outside the MESA tree (`work`/`binary`/test-suite baseline).
- `mesa_work_clear` — confirm-gated reset of a workspace's run output (resolved LOGS/photos/plots/run state); never touches inlists/src.
- `mesa_work_inlist_set` — set a control, format-preserving + backed up; redirects to the chain file that owns the namelist.
- `mesa_work_inlist_show` — the resolved inlist chain + effective output paths, plus set options vs MESA defaults.

**Execute & monitor — `mesa_run_*`**
- `mesa_run_start` / `mesa_run_status` / `mesa_run_stop` — start a run detached (guards a fresh run over existing output), monitor via JSON status (latest model's columns; a `binary` block for two-star runs), cancel.
- `mesa_run_gyre` — run GYRE on a pulsation model and parse its mode summary (when GYRE is built).

**Read & analyze data — `mesa_data_*`**
- `mesa_data_history` — read a sliced/downsampled `history.data` (resolved log dir + filename; `star` selector for binary).
- `mesa_data_column` — look up an output column (`kind="history"|"profile"`).
- `mesa_data_analyze` — `kind="history"` (stellar state, core masses, abundances, phase, TAMS — or **orbital** diagnostics with `star="binary"`) / `kind="profile"` (mixing zones, abundances, burning regions).
- `mesa_data_library` — list libraries (no arg) or parse one (networks, solar abundances, isotopes, colors; inventory for the rest).
- `mesa_data_rate` — `action="get"` (REACLIB fit sets + citation + rate at T9) / `"set_factor"` (scale a reaction via `special_rate_factor`).

**Visualization — `mesa_plot_*`**
- `mesa_plot_make` — `kind="history"` (presets `hr`, `kippenhahn`, **`binary`** orbital) / `kind="profile"` (preset `abundance`); matplotlib -> inline PNG.
- `mesa_plot_view` — `action="latest"` (inline image) / `"list"` (with model numbers).
- `mesa_plot_pgstar` — enable headless PGSTAR **and** pgbinary file output (located via the resolved inlist chain).
- `mesa_plot_live` — `action="open"|"close"` a separate auto-refreshing desktop window that follows a run's newest plot (where a display exists).

The telemetry/analysis/plotting tools take a `star` selector (`1`/`2`/`binary`) for binary runs.

## Support & limitations

Built and tested primarily around **single-star evolution**. Treat "⚠️" rows as **not fully tested**.

| Area | Status |
|---|---|
| **Single-star (`star`)** — diagnostics, docs/option lookup, test-suite replication, workspaces, inlist editing, run + monitor, telemetry/analysis/plotting | ✅ Supported & exercised |
| **Inlist-chain resolver** — entry inlist (CLI arg / `MESA_INLIST` / `inlist`) + recursive `read_extra_*` chain -> real `log_directory`/`star_history_name`/`photo_directory`; used by telemetry/runner/viz/inlist | ✅ Supported (single-star & binary) |
| **Nuclear rates (`net`/REACLIB)** and the **network / Lodders-abundance / isotope** data libraries | ✅ Supported |
| **`binary`** — template + all three namelists in `mesa_docs_option`; run + per-component telemetry; orbital `mesa_data_analyze`/`mesa_plot_make` (`star="binary"`); pgbinary file output | ⚠️ Supported, lightly tested |
| **GYRE** — run on a pulsation model + parse modes (`mesa_run_gyre`, when GYRE is built) | ⚠️ Runnable; the MESA->GYRE pulse-file step isn't configured yet |
| **`astero`** — `&astero_search_controls` options via the reference layer | ⚠️ Partial (no asteroseismic search workflow) |
| **`colors`** — filter sets + stellar-model grids via `mesa_data_library` | ⚠️ Parsed/inventoried (no magnitude pipeline yet) |
| **`eos` / `kap` / `atm` / `ionization`** | ⚠️ Options (where they ship `.defaults`) + structured inventory; no numeric evaluation |
| **`adipls`** (alternative oscillation code), **`stella`** (radiation-hydro light curves) | ❌ Not driven (standalone executables) |
| **Platform** | macOS (Apple Silicon) tested; Linux supported by design but less exercised; Windows unsupported |

### Module coverage (MESA root)

Science modules: `star` ✅; `binary` ⚠️; `net`/`rates`/`chem` ✅; `eos`/`kap`/`atm`/`ionization` ⚠️ (reference + inventory); `colors` ⚠️; `astero` ⚠️; `gyre` ⚠️; `adipls`/`stella` ❌. The numerical-infrastructure libraries (`const`, `math`, `mtx`, `num`, `auto_diff`, `turb`, `neu`, `star_data`, `interp_1d/2d`, `utils`) are internal and out of scope. Broadening this is tracked as **Phase 14** in the [roadmap](docs/roadmap.md).

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
