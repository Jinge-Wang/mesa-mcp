# TODO: Codex (OpenAI) port (stub)

Not implemented yet. Port from the canonical `../../claude-code/mesa/`.

Expected Codex layout:
- `.codex-plugin/plugin.json` — manifest with an `interface` block (`displayName`, `defaultPrompt`, …)
  and `mcpServers: "./.mcp.json"`.
- `.mcp.json` — the MESA MCP server config.
- `skills/mesa-agent/` — copy of the canonical skill.

The MCP server itself is platform-agnostic; only the packaging differs.
