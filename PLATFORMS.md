# Using the MESA MCP server across AI coding hosts

The server speaks the standard [Model Context Protocol](https://modelcontextprotocol.io), so it
works with any MCP-capable AI coding assistant. The same server (`uv run --directory <repo> python
main.py`) is used everywhere; only the **registration** and the **agent-guidance** delivery differ.

Replace `/absolute/path/to/mesa-mcp` below with your clone's path (the one `install.sh` detects).

## Support status

| Host | Status | Register the MCP server | Agent guidance | Example session |
| :--- | :--- | :--- | :--- | :--- |
| **Claude Code** (VS Code) | ✅ Supported (primary) | plugin or project `.mcp.json` | `skills/mesa-agent/` (auto-loaded) | — |
| **Antigravity CLI** | ✅ Supported | `~/.gemini/config/mcp_config.json` | `marketplace/mesa-agent.md` (as context) | [docs/sample-agy-cli.html](docs/sample-agy-cli.html) |
| **Gemini CLI** | ⚠️ Obsolete → use Antigravity | `gemini mcp add …` | `GEMINI.md` | [docs/sample-gemini-cli.html](docs/sample-gemini-cli.html) |
| **Cursor / Codex / Copilot CLI** | 🔜 Planned (stubs in `marketplace/`) | — | — | — |

> **Gemini CLI is being retired** (it stopped serving Google One / unpaid tiers on 18 Jun 2026).
> If you use Google models, install **Antigravity CLI** instead — the MCP server and tools are
> identical, only the registration differs.

## Prerequisites (all hosts)

1. [`uv`](https://docs.astral.sh/uv/) installed.
2. A working local MESA with a `load_mesa` shell function (sets `MESA_DIR` + sources the SDK).
3. From the repo root: `./install.sh` (verifies `uv`, runs `uv sync`, writes the paths, prints the
   per-host commands).

## Per-host setup

### Claude Code (VS Code) — primary
```bash
claude plugin marketplace add /absolute/path/to/mesa-mcp/marketplace
claude plugin install mesa@mesa-mcp
# …or just the MCP server:
claude mcp add mesa -- uv run --directory /absolute/path/to/mesa-mcp python main.py
```
The `mesa-agent` skill (workflows + guardrails) loads automatically with the plugin.

### Antigravity CLI
Antigravity reads MCP servers from `~/.gemini/config/mcp_config.json`. Create/merge:
```json
{
  "mcpServers": {
    "mesa": {
      "command": "uv",
      "args": ["run", "--directory", "/absolute/path/to/mesa-mcp", "python", "main.py"]
    }
  }
}
```
For agent guidance, load [`marketplace/mesa-agent.md`](marketplace/mesa-agent.md) as a context file
(the condensed rules + tool map). Reload Antigravity afterward.

### Gemini CLI (obsolete)
```bash
gemini mcp add mesa uv run --directory /absolute/path/to/mesa-mcp python main.py
```
Place [`marketplace/gemini/mesa/GEMINI.md`](marketplace/gemini/mesa/GEMINI.md) as a `GEMINI.md` in
your project for guidance. Prefer Antigravity going forward.

### Cursor / Codex / Copilot CLI
Stub entries exist under `marketplace/<host>/mesa/` with `TODO.md` notes; not yet wired up. The MCP
server itself is host-agnostic — registering it via each host's MCP config will work; the packaging
is what's pending.

## Notes

- The example sessions in `docs/` are anonymized transcripts of building and running a 1 M⊙ star
  with Antigravity and Gemini CLI — useful for seeing the expected tool flow.
- Whatever the host, the agent should follow the same guardrails (confirm the workspace directory and
  any run, never invent inlist options); these live in `skills/mesa-agent/` (Claude) and the
  condensed `marketplace/mesa-agent.md` (other hosts).
