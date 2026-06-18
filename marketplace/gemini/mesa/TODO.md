# TODO: Gemini port (stub)

Not implemented yet. Port from the canonical `../../claude-code/mesa/`.

Gemini CLI packaging is TBD. Likely:
- Register the MESA MCP server in the Gemini CLI MCP settings (`~/.gemini/settings.json` `mcpServers`).
- Provide the `mesa-agent` guidance as a system prompt / context file equivalent.

The MCP server itself is platform-agnostic (`python main.py`); only the packaging differs.
