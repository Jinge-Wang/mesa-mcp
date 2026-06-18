# AGENTS.md — Start Here

This file is loaded automatically by AI coding agents. **Read it before doing anything in this
repository.**

## What this project is

`mesa-mcp` is a Python [Model Context Protocol](https://modelcontextprotocol.io) server that lets
an AI coding agent drive a local installation of **MESA** (Modules for Experiments in Stellar
Astrophysics): search documentation, replicate verified test-suite setups, reuse the community's
shared inlists and publications, and execute MESA's build/run toolchain inside the user's sourced
shell environment.

Primary host workflow: **VS Code + the Claude extension.** The design is kept portable so it can
later ship to Cursor / Codex / Copilot CLI / Gemini.

## Before you write code: read `agent_context/` in this order

1. [`agent_context/assumptions.md`](agent_context/assumptions.md) — the verified facts about this
   machine, the two MESA installs, and the environment. Don't re-derive these; trust them but
   verify a path still exists before depending on it.
2. [`agent_context/rules.md`](agent_context/rules.md) — non-negotiable guardrails.
3. [`agent_context/coding_style.md`](agent_context/coding_style.md) — how code in this repo is written.
4. [`agent_context/architecture.md`](agent_context/architecture.md) — module map and data flow.
5. [`agent_context/glossary.md`](agent_context/glossary.md) — MESA domain terms.

The phased roadmap lives in [TRACKER.md](TRACKER.md).

## The five rules you must never break

1. **MESA core is read-only.** Never create, edit, or delete anything under a MESA install
   (`$MESA_DIR`). All work happens in sibling workspace folders outside the MESA tree.
2. **Dependencies need explicit user approval.** Never run `uv add` / `pip install` yourself.
   Propose the exact command and the `pyproject.toml` diff, then stop and let the user run it.
3. **Prefer first-party logic over `shmesa`.** `shmesa` is on PATH but the user has hit bugs in it;
   never make a tool depend on it. It is an optional convenience callable via `mesa_execute_shell`.
4. **Local-first, then network.** Read the local `$MESA_DIR/docs/source/*.rst` before reaching the
   internet. JS-rendered pages (Sphinx search, Zenodo records) must be accessed via local files or
   REST APIs, never by scraping the rendered HTML.
5. **Patch, don't overwrite.** Never rewrite a whole `inlist` or `run_star_extras.f90`. Make
   precise, format-preserving edits.

## Two rule sets, two audiences (don't confuse them)

- **`agent_context/`** (this folder) guides the agent **developing this server** — i.e. you, right now.
- **`skills/mesa-agent/`** guides the agent **using MESA through this server at runtime**, and ships
  inside the Claude plugin. When you edit one, check whether the other needs the same change.
