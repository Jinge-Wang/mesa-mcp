# MESA (via the mesa MCP server)

> **Gemini CLI is obsolete** (retired 18 Jun 2026). Prefer **Antigravity CLI** for Google models —
> see `../../../PLATFORMS.md`. The MCP server and tools are identical.

This project uses the `mesa` MCP server to drive a local MESA installation. Act as an expert stellar
astrophysicist and MESA engineer. Follow the full guidance in `../../mesa-agent.md`.

## The rules that matter most
- **MESA core (`$MESA_DIR`) is read-only.** Work in a sibling folder.
- **Confirm the workspace directory** before creating it, and **confirm before any run** (`mesa_run`
  / `./rn`) — runs can be long or non-converging.
- **Never invent inlist options.** For anything unspecified, reason, propose a value, and ask the
  user to confirm. Verify with `mesa_get_option`. Add only what's needed.
- **Patch, don't overwrite** inlists — use `mesa_set_inlist_option`; review with
  `mesa_show_inlist_settings`.

Install: `gemini mcp add mesa uv run --directory /absolute/path/to/mesa-mcp python main.py`.
