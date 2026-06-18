"""Web knowledge sources: community inlists (marketplace) and publications (Zenodo).

These are network-only (no local equivalent) and import httpx/bs4 lazily. Downloads land
in the session scratch dir (config.session_dir), purged when the server exits.
"""
