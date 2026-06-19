# Development — the dev-agent primer

This folder (`docs/development/`) is the canonical, always-loaded context for any AI agent
**building** `mesa-mcp`. It exists so that every coding session starts from the same verified facts,
guardrails, and style — instead of re-deriving them from scratch and drifting.

> Audience note: this is for the agent **developing the server**. The agent that **uses** MESA
> through the server at runtime is guided by [`../../skills/mesa-agent/`](../../skills/mesa-agent/)
> instead. Keep the two in sync when a change applies to both.

## Files

| File | What it holds | When to read |
|---|---|---|
| [`assumptions.md`](assumptions.md) | Verified facts: machine layout, the two MESA installs, env, deps | First, every session |
| [`rules.md`](rules.md) | Non-negotiable guardrails (safety, sandbox, process) | Before any edit |
| [`coding_style.md`](coding_style.md) | Python / FastMCP conventions for this repo | Before writing code |
| [`architecture.md`](architecture.md) | Module map + data-flow (version → docs → search/fetch; execution) | When adding/moving modules |
| [`glossary.md`](glossary.md) | MESA domain vocabulary | When a MESA term is unfamiliar |

## How to use this folder

1. Read [`assumptions.md`](assumptions.md) and [`rules.md`](rules.md) at the start of a session.
2. Trust the recorded facts, but **verify a specific path/function still exists** before depending
   on it (installs get re-pointed, versions change).
3. When you learn a new durable fact or make a new design decision, **update the relevant file
   here** so the next session inherits it. This folder is living documentation, not a one-time dump.
4. If a rule here conflicts with a direct user instruction, the **user wins** — then update the file.
