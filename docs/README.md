# Documentation

The documentation hub for `mesa-mcp`. Start at the repository [README](../README.md) for the
overview, tool list, installation, and platform support.

## Map

| Path | What it is | Audience |
|---|---|---|
| [development/](development/) | Guidance for agents/contributors **developing this server** (rules, architecture, assumptions, style, glossary). Start at [development/README.md](development/README.md). | Builders of the server |
| [infrastructure.md](infrastructure.md) | Runtime, package layout, core data flow, caching & ephemerality, distribution. | Builders of the server |
| [roadmap.md](roadmap.md) | The phased implementation tracker (history + any remaining ideas). | Anyone tracking progress |
| [examples/](examples/) | Recorded example sessions (Antigravity, Gemini CLI). | Anyone evaluating the server |

## Related (outside `docs/`)

- [../AGENTS.md](../AGENTS.md) — the start-here entry point auto-loaded by AI agents.
- [../skills/mesa-agent/](../skills/mesa-agent/) — the **runtime** skill that ships in the plugin and
  guides the agent *using* MESA through the server (distinct from `development/`, which guides the
  agent *building* the server).
