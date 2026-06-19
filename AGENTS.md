# AGENTS.md

**Full start-here guide:** [docs/AGENTS.md](docs/AGENTS.md) — read it before doing anything in this repo.

`mesa-mcp` is a Model Context Protocol server that drives a local **MESA** install. Quick links:
- Dev guidance: [docs/development/](docs/development/) · Roadmap: [docs/roadmap.md](docs/roadmap.md)
- Runtime skill (ships in the plugin): [skills/mesa-agent/](skills/mesa-agent/)

The five non-negotiable rules (MESA core is read-only; dependencies need explicit user approval;
prefer first-party logic over `shmesa`; local-first then network; patch, don't overwrite) are spelled
out in [docs/AGENTS.md](docs/AGENTS.md).
