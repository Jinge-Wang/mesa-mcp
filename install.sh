#!/usr/bin/env bash
#
# install.sh — set up the MESA MCP server on macOS / Linux for VS Code + Claude.
#
# What it does (in order):
#   1. Verifies `uv` is available.
#   2. Installs the Python dependencies into .venv via `uv sync` (asks first).
#   3. Smoke-tests that the server imports.
#   4. Writes the absolute repo path into the .mcp.json files.
#   5. Assembles the Claude plugin (copies the canonical skill into it).
#   6. Prints the registration commands for Claude Code / VS Code.
#
# It never touches the MESA installation. Re-runnable.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ASSUME_YES=0
[ "${1:-}" = "-y" ] || [ "${1:-}" = "--yes" ] && ASSUME_YES=1

info()  { printf '\033[1;34m[mesa-mcp]\033[0m %s\n' "$*"; }
warn()  { printf '\033[1;33m[mesa-mcp]\033[0m %s\n' "$*" >&2; }
die()   { printf '\033[1;31m[mesa-mcp]\033[0m %s\n' "$*" >&2; exit 1; }

confirm() {
  # confirm "question" -> 0 if yes. Auto-yes with -y or when non-interactive.
  if [ "$ASSUME_YES" = "1" ] || [ ! -t 0 ]; then return 0; fi
  printf '\033[1;36m[mesa-mcp]\033[0m %s [Y/n] ' "$1"
  read -r reply
  case "$reply" in [nN]*) return 1;; *) return 0;; esac
}

# 1. uv (Python package/venv manager used to run the server)
if ! command -v uv >/dev/null 2>&1; then
  warn "uv is not installed. It manages this server's Python environment."
  cat <<'UVHELP'

  Install uv, then re-run ./install.sh. Official guide:
    https://docs.astral.sh/uv/getting-started/installation/

  macOS / Linux (standalone installer):
    curl -LsSf https://astral.sh/uv/install.sh | sh

  macOS (Homebrew):
    brew install uv

  (After installing, open a new shell or `source` your profile so `uv` is on PATH.)
UVHELP
  die "uv is required — install it (see above) and re-run."
fi
info "Using uv: $(command -v uv)"

# 2. dependencies
info "Dependencies to install (from pyproject.toml): mcp, httpx, beautifulsoup4."
if confirm "Run 'uv sync' to install them into .venv now?"; then
  ( cd "$REPO_ROOT" && uv sync )
  info "Dependencies installed."
else
  warn "Skipped 'uv sync'. Network features (doc fallback, Phase 2 web tools) need httpx + beautifulsoup4."
fi

# 3. smoke test (uses the venv python directly; does not re-sync)
PYBIN="$REPO_ROOT/.venv/bin/python"
if [ -x "$PYBIN" ]; then
  if ( cd "$REPO_ROOT" && PYTHONPATH="$REPO_ROOT" "$PYBIN" -c "from mesa_mcp.server import mcp" ) 2>/dev/null; then
    info "Server import OK."
  else
    warn "Server import failed — check that 'uv sync' completed."
  fi
fi

# 4. write the absolute repo path into both .mcp.json files
write_mcp_json() {
  cat > "$1" <<JSON
{
  "mcpServers": {
    "mesa": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "$REPO_ROOT",
        "python",
        "main.py"
      ]
    }
  }
}
JSON
}
write_mcp_json "$REPO_ROOT/.mcp.json"
write_mcp_json "$REPO_ROOT/marketplace/claude-code/mesa/.mcp.json"
write_mcp_json "$REPO_ROOT/marketplace/gemini/mesa/mcp.json"
write_mcp_json "$REPO_ROOT/marketplace/antigravity/mesa/mcp_config.json"
info "Wrote MCP configs with repo path: $REPO_ROOT"

# 5. assemble the Claude plugin: single source of truth for the skill
PLUGIN_SKILLS="$REPO_ROOT/marketplace/claude-code/mesa/skills"
rm -rf "$PLUGIN_SKILLS"
mkdir -p "$PLUGIN_SKILLS"
cp -R "$REPO_ROOT/skills/." "$PLUGIN_SKILLS/"
info "Assembled plugin skill into marketplace/claude-code/mesa/skills/."

# 6. next steps
cat <<NEXT

$(info "Setup complete. Next steps:")

  VS Code Native MCP / GitHub Copilot:
    Open the Command Palette (Cmd/Ctrl+Shift+P) -> "MCP: Open User Configuration"
    and add the contents of: $REPO_ROOT/.mcp.json

  Claude VS Code Extension:
    Manually edit ~/.claude.json and paste the "mesa" JSON block from:
    $REPO_ROOT/.mcp.json

  Cline, Roo Code, or other VS Code Extensions:
    Copy the "mesa" JSON block from:
    $REPO_ROOT/.mcp.json
    ...and paste it into your extension's specific MCP settings file.

  Claude Code CLI (plugin + MCP server + skill):
    claude plugin marketplace add "$REPO_ROOT/marketplace"
    claude plugin install mesa@mesa-mcp
    # ...or just the server:  claude mcp add mesa -- uv run --directory "$REPO_ROOT" python main.py

  Antigravity CLI:
    add the "mesa" server to ~/.gemini/config/mcp_config.json
    (ready-made: $REPO_ROOT/marketplace/antigravity/mesa/mcp_config.json)
    load $REPO_ROOT/marketplace/mesa-agent.md as a context file.

  Gemini CLI (obsolete -> prefer Antigravity):
    gemini mcp add mesa uv run --directory "$REPO_ROOT" python main.py

  Full support matrix + details: the "Platform support" section of $REPO_ROOT/README.md
  
  Finally:
  1. Restart your client (relaunch the CLI, or use Cmd/Ctrl+Shift+P -> "Developer: Reload Window" in VS Code).
  2. Ask the AI: "Please call the mesa_env_info tool to confirm your toolchain is working."
NEXT