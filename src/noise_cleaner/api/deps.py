"""
Shared helpers used across all API route modules.
"""
from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Callable

from ..config import executor

_VIDEO_EXTS = frozenset(
    {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m2ts", ".ts", ".flv", ".wmv"}
)


def is_video(path: Path) -> bool:
    """Return True if *path* looks like a video container."""
    return path.suffix.lower() in _VIDEO_EXTS


def safe_name(raw: str | None) -> str:
    """Return filename string, never None."""
    return raw or "audio.wav"


async def run_in_thread(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """
    Run a blocking / CPU-bound function in the shared thread-pool without
    blocking the asyncio event loop.

    Usage::

        result = await run_in_thread(heavy_function, arg1, arg2, key=val)
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(executor, lambda: fn(*args, **kwargs))
