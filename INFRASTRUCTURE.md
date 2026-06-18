# Infrastructure Architecture

## Runtime

The server uses the official Python MCP SDK via the `FastMCP` decorator wrapper. It talks to the
host (VS Code + Claude extension) over **stdio** using JSON-RPC 2.0 frames. It executes MESA
workflows as subprocesses inside the user's **sourced** shell environment (so `MESA_DIR`,
`MESASDK_ROOT`, the SDK compilers, and `shmesa` are all present).

```text
┌──────────────────────────┐             ┌──────────────────────────┐
│  VS Code / Claude        │  <--stdio-->│   MESA MCP Server        │
│  (Orchestration Layer)   │   JSON-RPC  │   (Python / FastMCP)     │
└──────────────────────────┘             └────────────┬─────────────┘
                                                       │  build_env_context()
                                            source ~/.zshrc + load_mesa
                                                       ▼
                                         ┌──────────────────────────┐
                                         │  Sourced MESA Context    │
                                         │  ($MESA_DIR, SDK, shmesa)│
                                         └──────────────────────────┘
```

## Package layout (`mesa_mcp/`)

```
server.py        FastMCP instance, tool registration, main().
config.py        Docs base URL, cache dir, session temp dir, timeouts, env-var names.
environment.py   Source shell + load_mesa → MESA env; validation. (Moved from main.py.)
version.py       data/version_number → docs version (release vs git hash).
shell.py         Bounded command execution in the sourced env.
docs/            sources.py · fetch.py · index.py · search.py · test_suite.py
knowledge/       inlists.py · publications.py   (Phase 2)
tools/           info.py · knowledge.py · community.py · execution.py  (thin FastMCP wrappers)
```

`tools/` modules hold no logic — they validate inputs, call a logic module, and format the result.
The full living module map and responsibilities are in
[`agent_context/architecture.md`](agent_context/architecture.md).

## Core data flow

1. A tool calls `build_env_context()` (`environment.py`) to get the live MESA environment.
2. `version.py` maps `$MESA_DIR/data/version_number` → a docs version (release number or `latest`;
   `MESA_DOCS_VERSION` overrides).
3. `docs/sources.py` resolves the docs source: **local** `$MESA_DIR/docs/source/` if present, else
   the **network** base `https://docs.mesastar.org/en/<version>/`.
4. `docs/{index,search,fetch,test_suite}.py` serve content local-first; network is fallback.
5. `shell.py` runs commands in the sourced env, guarding writes to stay **outside** `$MESA_DIR`.

## Why local-first / APIs (not HTML scraping)

Local `docs/source/` is `.rst` **source** (no prebuilt HTML or `searchindex.js`), so search means
indexing the `.rst`. JS-rendered web pages can't be scraped: **Sphinx search** loads
`searchindex.js` client-side, and the **Zenodo records** page is a React app. Network access
therefore uses either the cached `searchindex.js` or documented **REST APIs** (Zenodo
`/api/records?communities=mesa&q=…`). The marketplace inlists page is static HTML and is safe to parse.

## Caching & ephemerality

- Built docs index → OS cache dir, keyed by version + docs mtime (rebuild only when stale).
- Network `searchindex.js` → persisted on disk, reused across prompts (no per-prompt re-download).
- Scraped tables → cached per session.
- Network **downloads** → a session temp dir created at startup, **purged on server exit**.

## Distribution

`marketplace/` follows a multi-platform plugin layout: `claude-code/mesa/` is populated (plugin manifest +
`.mcp.json` + the runtime skill); `cursor/`, `codex/`, `copilot-cli/`, `gemini/` are blank stubs
(`TODO.md`) marking future ports. `install.sh` handles the macOS/Linux Claude/VS Code path.
