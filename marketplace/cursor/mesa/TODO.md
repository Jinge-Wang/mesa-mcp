# TODO: Cursor port (stub)

Not implemented yet. Port from the canonical `../../claude-code/mesa/`.

Expected Cursor layout:
- `.cursor-plugin/plugin.json` — manifest with `displayName`, `mcpServers: "mcp.json"`, `skills: "skills"`.
- `mcp.json` (lowercase, not `.mcp.json`) — the MESA MCP server config.
- `skills/mesa-agent/` — copy of the canonical skill.

The MCP server itself is platform-agnostic (`python main.py`); only the packaging differs.
