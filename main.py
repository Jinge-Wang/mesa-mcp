"""Entry point for the MESA MCP server.

The implementation lives in the ``mesa_mcp`` package. Run the server with either
``python main.py`` (from the repo root) or ``python -m mesa_mcp.server``.
"""
from mesa_mcp.server import main

if __name__ == "__main__":
    main()
