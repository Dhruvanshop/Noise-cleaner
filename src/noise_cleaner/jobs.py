"""
In-memory job registry for background tasks.

Keeps track of every long-running job (status, timestamps, result / error).
A background sweep removes entries older than JOB_TTL_SECONDS so memory
doesn't grow unboundedly between restarts.
"""
from __future__ import annotations

import threading
import time
from enum import Enum
from typing import Any, Dict, Optional

from .config import JOB_TTL_SECONDS


class JobStatus(str, Enum):
    QUEUED     = "queued"
    PROCESSING = "processing"
    DONE       = "done"
    ERROR      = "error"


class JobRegistry:
    """
    Thread-safe mapping of  job_id → job dict.

    Each job dict contains:
        status       JobStatus
        created_at   float  (epoch seconds)
        started_at   float | None
        finished_at  float | None
        result       dict | None   (populated on DONE)
        error        str  | None   (populated on ERROR)
        + any extra keyword metadata passed to .create()
    """

    def __init__(self, ttl: int = JOB_TTL_SECONDS) -> None:
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._ttl  = ttl

    # ── lifecycle ────────────────────────────────────────────────────────────

    def create(self, job_id: str, **meta: Any) -> str:
        """Register a new QUEUED job and return its id."""
        with self._lock:
            self._jobs[job_id] = {
                "status":      JobStatus.QUEUED,
                "created_at":  time.time(),
                "started_at":  None,
                "finished_at": None,
                "result":      None,
                "error":       None,
                **meta,
            }
        return job_id

    def mark_processing(self, job_id: str) -> None:
        self._patch(job_id, status=JobStatus.PROCESSING, started_at=time.time())

    def mark_done(self, job_id: str, result: Dict[str, Any]) -> None:
        self._patch(
            job_id,
            status=JobStatus.DONE,
            result=result,
            finished_at=time.time(),
        )

    def mark_error(self, job_id: str, error: str) -> None:
        self._patch(
            job_id,
            status=JobStatus.ERROR,
            error=error,
            finished_at=time.time(),
        )

    # ── query ─────────────────────────────────────────────────────────────────

    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            entry = self._jobs.get(job_id)
            return dict(entry) if entry else None

    # ── maintenance ───────────────────────────────────────────────────────────

    def cleanup_expired(self) -> int:
        """Remove entries older than TTL.  Returns number of entries removed."""
        cutoff = time.time() - self._ttl
        with self._lock:
            expired = [k for k, v in self._jobs.items()
                       if v["created_at"] < cutoff]
            for k in expired:
                del self._jobs[k]
        return len(expired)

    def __len__(self) -> int:
        with self._lock:
            return len(self._jobs)

    # ── private ───────────────────────────────────────────────────────────────

    def _patch(self, job_id: str, **fields: Any) -> None:
        with self._lock:
            if job_id in self._jobs:
                self._jobs[job_id].update(fields)


#: Module-level singleton — import and use this everywhere.
registry: JobRegistry = JobRegistry()
