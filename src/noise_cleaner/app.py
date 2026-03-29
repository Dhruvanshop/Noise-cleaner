"""
FastAPI application factory.

Import ``app`` directly (e.g. for uvicorn) or call ``create_app()`` to get
a fresh instance (useful for testing).
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from .config import CLEANUP_INTERVAL, JOB_TTL_SECONDS, STATIC_DIR, TEMP_DIR, MAX_FILE_SIZE_BYTES
from .jobs import registry

log = logging.getLogger(__name__)


# ── file size validation middleware ───────────────────────────────────────────

class FileSizeValidationMiddleware(BaseHTTPMiddleware):
    """Reject requests with Content-Length exceeding MAX_FILE_SIZE_BYTES."""
    
    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length:
            if int(content_length) > MAX_FILE_SIZE_BYTES:
                raise HTTPException(
                    status_code=413,
                    detail=f"File size exceeds maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024*1024)}MB"
                )
        return await call_next(request)


# ── background cleanup ────────────────────────────────────────────────────────

async def _cleanup_loop(interval: int = CLEANUP_INTERVAL) -> None:
    """
    Runs forever in the background:
    1. Removes expired job entries from the in-memory registry.
    2. Deletes orphaned temp directories whose mtime is past TTL.
    """
    while True:
        await asyncio.sleep(interval)
        try:
            n = registry.cleanup_expired()
            if n:
                log.info("Job registry: removed %d expired entries", n)

            cutoff = time.time() - JOB_TTL_SECONDS
            removed = 0
            for d in TEMP_DIR.iterdir():
                if d.is_dir() and d.stat().st_mtime < cutoff:
                    shutil.rmtree(d, ignore_errors=True)
                    removed += 1
            if removed:
                log.info("Temp cleanup: removed %d stale task directories", removed)
        except Exception:
            log.exception("Error in periodic cleanup task")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _task = asyncio.create_task(_cleanup_loop())
    log.info(
        "Noise Cleaner started | temp=%s | workers=%s",
        TEMP_DIR, app.state.max_workers if hasattr(app.state, "max_workers") else "?",
    )
    yield
    _task.cancel()
    log.info("Noise Cleaner shutting down")


# ── app factory ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    from .api import (
        analyze, batch, caption, convert, denoise, dereverberate,
        normalize, pages, remix, repair, stems, transcribe, trim, video,
    )

    _app = FastAPI(
        title="Noise Cleaner",
        description=(
            "Local-first audio & video processing API. "
            "All processing happens on your machine — no data sent anywhere."
        ),
        version="2.0.0",
        docs_url="/api/docs",
        redoc_url=None,
        lifespan=_lifespan,
    )

    # Add middleware
    _app.add_middleware(FileSizeValidationMiddleware)

    # Serve everything under /static/ from the static directory
    _app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # HTML page routes (no prefix)
    _app.include_router(pages.router)

    # API routes (prefixed /api)
    _app.include_router(denoise.router,    prefix="/api")
    _app.include_router(stems.router,      prefix="/api")
    _app.include_router(normalize.router,  prefix="/api")
    _app.include_router(convert.router,    prefix="/api")
    _app.include_router(trim.router,       prefix="/api")
    _app.include_router(video.router,      prefix="/api")
    _app.include_router(caption.router,    prefix="/api")
    _app.include_router(transcribe.router, prefix="/api")
    _app.include_router(repair.router,       prefix="/api")
    _app.include_router(dereverberate.router, prefix="/api")
    _app.include_router(analyze.router,      prefix="/api")
    _app.include_router(remix.router,        prefix="/api")
    _app.include_router(batch.router,        prefix="/api")

    @_app.get("/health")
    async def health_check():
        """Health check endpoint for load balancers and monitoring."""
        return {
            "status": "healthy",
            "version": "2.0.0",
            "environment": os.getenv("ENVIRONMENT", "development"),
        }

    return _app


#: Module-level singleton — ``uvicorn noise_cleaner.app:app``
app = create_app()
