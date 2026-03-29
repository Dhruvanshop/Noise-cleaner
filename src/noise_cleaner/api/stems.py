"""
/api/stems          — POST: enqueue stem-separation job, returns {job_id}
/api/jobs/{id}      — GET:  poll job status / result
/api/stem_download  — GET:  download a single stem file
"""
from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import TEMP_DIR, executor
from ..jobs import registry
from ..stem import _DEMUCS_AVAILABLE, separate_file
from ..video import _FFMPEG_AVAILABLE, extract_audio
from .deps import is_video, safe_name

router = APIRouter(tags=["stems"])

_MIME = {
    "mp3": "audio/mpeg", "flac": "audio/flac",
    "ogg": "audio/ogg",  "m4a": "audio/mp4", "wav": "audio/wav",
}


# ── enqueue ───────────────────────────────────────────────────────────────────

@router.post("/stems")
async def api_stems(
    background_tasks: BackgroundTasks,
    file:          UploadFile = File(...),
    stems:         str        = Form("vocals,drums,bass,other"),
    output_format: str        = Form("wav"),
    model_name:    str        = Form("htdemucs"),   # htdemucs | htdemucs_6s
):
    """
    Enqueue a stem-separation job.  Returns ``{"job_id": "…"}`` immediately.
    Poll ``GET /api/jobs/{job_id}`` until ``status`` is ``"done"`` or ``"error"``.
    """
    if not _DEMUCS_AVAILABLE:
        raise HTTPException(503, "Demucs not installed — run: pip install demucs")

    job_id   = str(uuid.uuid4())
    task_dir = TEMP_DIR / job_id
    task_dir.mkdir(parents=True)

    suffix     = Path(safe_name(file.filename)).suffix.lower() or ".wav"
    input_path = task_dir / f"input{suffix}"
    input_path.write_bytes(await file.read())

    registry.create(job_id, filename=safe_name(file.filename), tool="stems")

    background_tasks.add_task(
        _run_stems_job,
        job_id, input_path, task_dir,
        stems, output_format, model_name,
    )
    return {"job_id": job_id}


# ── background worker ─────────────────────────────────────────────────────────

async def _run_stems_job(
    job_id:        str,
    input_path:    Path,
    task_dir:      Path,
    stems_str:     str,
    output_format: str,
    model_name:    str,
) -> None:
    registry.mark_processing(job_id)
    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            executor,
            _blocking_stems,
            input_path, task_dir, stems_str, output_format, model_name,
        )
        if result["ok"]:
            (task_dir / ".tool").write_text("stems")
            registry.mark_done(job_id, {
                "task_id":       job_id,
                "stems":         {name: f"/api/stem_download/{job_id}/{name}"
                                  for name in result["stems"]},
                "duration":      result["duration"],
                "samplerate":    result["samplerate"],
                "channels":      result["channels"],
                "output_format": output_format,
                "model":         model_name,
            })
        else:
            registry.mark_error(job_id, result.get("error", "Stem separation failed"))
    except Exception as exc:
        registry.mark_error(job_id, str(exc))


def _blocking_stems(
    input_path:    Path,
    task_dir:      Path,
    stems_str:     str,
    output_format: str,
    model_name:    str,
) -> dict:
    """Pure-blocking execution — called from the thread pool."""
    audio_in = input_path
    if is_video(input_path):
        if not _FFMPEG_AVAILABLE:
            return {"ok": False, "error": "ffmpeg is required for video files"}
        extracted = task_dir / "audio_extracted.wav"
        res = extract_audio(input_path, extracted)
        if not res.get("ok"):
            return {"ok": False, "error": res.get("error", "Audio extraction failed")}
        audio_in = extracted

    stems_list = [s.strip() for s in stems_str.split(",") if s.strip()]
    return separate_file(
        audio_in,
        task_dir / "stems",
        stems_list,
        output_format,
        model_name=model_name,
    )


# ── poll ──────────────────────────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
async def api_job_status(job_id: str):
    """
    Poll for job status.

    Returns::

        {
          "status":      "queued" | "processing" | "done" | "error",
          "created_at":  <epoch>,
          "started_at":  <epoch> | null,
          "finished_at": <epoch> | null,
          "result":      { task_id, stems, duration, … } | null,
          "error":       "…" | null,
        }
    """
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(404, "Job not found or expired")
    return job


# ── download ──────────────────────────────────────────────────────────────────

@router.get("/stem_download/{task_id}/{stem_name}")
async def stem_download(task_id: str, stem_name: str):
    stems_dir = TEMP_DIR / task_id / "stems"
    matches   = list(stems_dir.glob(f"{stem_name}.*"))
    if not matches:
        raise HTTPException(404, "Stem not found")
    path = matches[0]
    ext  = path.suffix.lstrip(".")
    return FileResponse(
        str(path),
        media_type=_MIME.get(ext, "audio/wav"),
        headers={"Content-Disposition": f'attachment; filename="{stem_name}.{ext}"'},
    )
