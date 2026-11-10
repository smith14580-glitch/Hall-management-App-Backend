"""Vercel entrypoint.

Vercel detects a FastAPI app by the `app` instance at a supported entrypoint
(index.py / app.py / app/main.py / ...) and routes every request to it while
preserving the original path. Do NOT rewrite requests to /api/*: legacy
file-based routing replaces the path with the function path, so FastAPI only
sees "/api/index" and answers 404 for every route (including /docs).
"""

from app.main import app  # noqa: F401
