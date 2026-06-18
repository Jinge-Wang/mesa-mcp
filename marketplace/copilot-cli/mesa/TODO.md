# TODO: GitHub Copilot CLI port (stub)

Not implemented yet. Port from the canonical `../../claude-code/mesa/`.

Expected Copilot CLI layout:
- `plugin.json` — manifest at the top level (NOT in a hidden directory), with `mcpServers: "./.mcp.json"`.
- `.mcp.json` — the MESA MCP server config.
- `skills/mesa-agent/` — copy of the canonical skill.

The MCP server itself is platform-agnostic; only the packaging differs.
