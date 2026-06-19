# mesa — Antigravity CLI

Antigravity is Google's successor to the (now obsolete) Gemini CLI. The MESA MCP server and tools
are identical; only registration differs.

## Register the MCP server
Antigravity reads MCP servers from `~/.gemini/config/mcp_config.json`. Copy or merge
[`mcp_config.json`](mcp_config.json) there, replacing `/absolute/path/to/mesa-mcp` with your clone's
path (`install.sh` prints it):

```bash
mkdir -p ~/.gemini/config
# then edit ~/.gemini/config/mcp_config.json to include the "mesa" server below
```
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

## Agent guidance
Load [`../../mesa-agent.md`](../../mesa-agent.md) as a context/system file so the agent follows the
MESA guardrails (confirm the workspace + any run; never invent inlist options; patch don't
overwrite). Reload Antigravity afterward, then try: *"list my current MESA information."*

See the example session in [`../../../docs/examples/sample-antigravity-cli.html`](../../../docs/examples/sample-antigravity-cli.html).
