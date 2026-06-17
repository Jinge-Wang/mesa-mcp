# MESA MCP Automation Server

An intelligent, physics-aware automation layer built on top of the Model Context Protocol (MCP). This server acts as a bridge between LLM orchestration clients (such as VS Code Copilot, Claude Desktop, or Continue) and a local installation of MESA (Modules for Experiments in Stellar Astrophysics).
This repo is currently under active development and is not functional yet!

## Project Goals

1. **Deterministic Environment Execution**: Automatically wrap all compiler (`./mk`) and runtime (`./rn`, `./re`) workflows inside the user's isolated local MESA toolchain environment.
2. **Dynamic Knowledge Fetching**: Provide direct tools for live documentation scraping and targeted web search against `docs.mesastar.org` to eliminate LLM halluncinations regarding parameter formatting.
3. **Deep Test-Suite Parsing**: Implement granular parsers tailored for MESA's test-suite indexes. The server must be capable of extracting test explanations and parsing reference `inlist` code blocks to replicate verified baseline configurations.
4. **Intent-Based Workspace Orchestration**: Interpret high-level scientific goals (e.g., "Evolve a $1.5 M_\odot$ star with diffusion" or "Model a coupled binary mass-transfer system") and autonomously provision, link, and structure the necessary work folders outside the core MESA tree.
5. **Context-Optimized Telemetry Slicing**: Avoid injecting sprawling ASCII tables into the LLM context. Programmatically configure output arrays via `history_columns.list` and read filtered, downsampled data slices.

## System Topology

```text
/your-parent-directory/
├── mesa/                 <── Core MESA Codebase & Verification Test Suites (Read-Only Target)
└── mesa-mcp-server/      <── This Repository: Python FastMCP Server Architecture
