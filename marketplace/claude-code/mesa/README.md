# mesa (Claude Code plugin)

Bundles the MESA MCP server and the `mesa-agent` skill.

- **MCP server** (`.mcp.json`) — launches the server from this repo via `uv run`. The absolute
  `--directory` path is set for this machine by `install.sh`.
- **Skill** (`skills/mesa-agent/`) — assembled by `install.sh`, which copies the canonical skill
  from the repo-root `skills/mesa-agent/` so there is a single source of truth.

## Install

From the repository root:

```bash
./install.sh
```

Then register the marketplace and plugin with Claude Code:

```bash
claude plugin marketplace add /path/to/mesa-mcp/marketplace
claude plugin install mesa@mesa-mcp
```

(`install.sh` prints the exact commands with the detected path.)
