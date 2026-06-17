```markdown
# Infrastructure Architecture

## Runtime Architecture

The server leverages the official Python MCP SDK using the `FastMCP` protocol decorator wrapper. Communication between the host development environment and the server takes place via standard input/output (stdio) channels using serialized JSON-RPC 2.0 frames.

```text
┌──────────────────────────┐             ┌──────────────────────────┐
│  VS Code / LLM Client    │  ◄──stdio──►│   MESA Custom Server     │
│  (Orchestration Layer)   │   JSON-RPC  │   (Python / FastMCP)     │
└──────────────────────────┘             └────────────┬─────────────┘
                                                      │
                                           Subprocess Executions
                                                      │
                                                      ▼
                                         ┌──────────────────────────┐
                                         │  Local Sourced Context   │
                                         │  (gfortran / MESA SDK)   │
                                         └──────────────────────────┘
