"""Documentation access: source resolution, fetching, indexing, search, test suite.

Everything here is local-first (read $MESA_DIR/docs/source/*.rst) and falls back to the
network only when local docs are unavailable. Third-party HTTP/parsing libraries are
imported lazily inside the network paths so local features work without them.
"""
