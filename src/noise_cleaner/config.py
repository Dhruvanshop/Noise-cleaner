"""
Central configuration for Noise Cleaner.

All tuneable knobs live here; downstream modules import from this file
so changing an environment variable is the only thing needed to reconfigure.
"""
from __future__ import annotations

import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# ── environment ─────────────────────────────────────────────────────────────
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
IS_PRODUCTION = ENVIRONMENT == "production"

# ── paths ──────────────────────────────────────────────────────────────────
BASE_DIR   = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"

TEMP_DIR = Path(os.getenv("NC_TEMP_DIR", tempfile.gettempdir())) / "noise_cleaner"
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# ── file limits ─────────────────────────────────────────────────────────────
#: Maximum upload file size in bytes (default: 100 MB)
MAX_FILE_SIZE_BYTES: int = int(os.getenv("MAX_FILE_SIZE_MB", "100")) * 1024 * 1024

# ── features ────────────────────────────────────────────────────────────────
#: Enable AI denoising (set to 'false' for commercial use due to CC-BY-NC license)
ENABLE_AI_DENOISE: bool = os.getenv("ENABLE_AI_DENOISE", "false").lower() == "true"

# ── job lifecycle ──────────────────────────────────────────────────────────
#: Seconds after creation before a job (and its temp directory) is deleted.
JOB_TTL_SECONDS: int = int(os.getenv("NC_JOB_TTL", "7200"))        # default 2 h

#: How often the cleanup sweep runs (seconds).
CLEANUP_INTERVAL: int = int(os.getenv("NC_CLEANUP_INTERVAL", "1800"))  # 30 min

# ── concurrency ─────────────────────────────────────────────────────────────
#: Maximum concurrent CPU-bound jobs (stem sep, AI denoise, transcribe…).
#: Defaults to half the CPU cores (min 2) so the machine stays responsive.
MAX_WORKERS: int = int(
    os.getenv("NC_WORKERS", str(max(2, (os.cpu_count() or 4) // 2)))
)

#: Shared thread-pool used by every heavy API handler.
#: Import this object — do NOT create additional executors.
executor = ThreadPoolExecutor(
    max_workers=MAX_WORKERS,
    thread_name_prefix="nc-worker",
)
