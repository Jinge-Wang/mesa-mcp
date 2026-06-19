# mesa — Gemini CLI

> ⚠️ **Gemini CLI is obsolete** (retired 18 Jun 2026 for Google One / unpaid tiers). Use
> **Antigravity CLI** instead — see [`../../antigravity/mesa/`](../../antigravity/mesa/) and the
> "Platform support" section of [`../../../README.md`](../../../README.md). The MESA tools are identical.

## Register the MCP server
```bash
gemini mcp add mesa uv run --directory /absolute/path/to/mesa-mcp python main.py
```
(Replace the path with your clone; `install.sh` prints the exact command.)

## Agent guidance
Place [`GEMINI.md`](GEMINI.md) (a condensed copy of [`../../mesa-agent.md`](../../mesa-agent.md)) in
your project so Gemini follows the MESA guardrails. Reload Gemini afterward.
