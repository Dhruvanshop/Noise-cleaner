"""
Entry-point shim — all logic has moved to ``app.py`` and ``api/``.

Kept here so existing CLI / entry-point references continue to work.
"""
from __future__ import annotations

from .app import app  # noqa: F401  (re-exported for uvicorn)


def serve(
    host: str = "0.0.0.0",
    port: int = 8765,
    open_browser: bool = True,
    log_level: str = "info",
) -> None:
    """
    Start the Noise Cleaner web UI.

    The server is intentionally single-process so the in-memory job registry
    is shared across all requests.  For horizontal scaling behind a load
    balancer, replace ``registry`` with a Redis-backed implementation and
    run multiple uvicorn workers.
    """
    import webbrowser
    import uvicorn

    url = f"http://{host}:{port}"
    print(f"\n🎵  Noise Cleaner  →  {url}\n")
    if open_browser and host in ("127.0.0.1", "localhost", "0.0.0.0"):
        webbrowser.open(f"http://127.0.0.1:{port}")

    uvicorn.run(
        "noise_cleaner.app:app",
        host=host,
        port=port,
        log_level=log_level,
        access_log=True,
    )
