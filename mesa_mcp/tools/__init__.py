"""Thin FastMCP tool wrappers.

Each module exposes ``register(mcp)`` which declares its tools on the shared FastMCP
instance. Wrappers validate inputs, call a logic module (environment, shell, docs, …),
and format the result — they contain no business logic themselves.
"""
