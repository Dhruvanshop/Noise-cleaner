"""/api/analyze — BPM, musical key, loudness, spectral analysis."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import TEMP_DIR
from ..analyzer import analyze_audio
from .deps import run_in_thread, safe_name

router = APIRouter(tags=["analyze"])


@router.post("/analyze")
async def api_analyze(
    file: UploadFile = File(...),
):
    """
    Analyse audio: BPM, musical key, integrated loudness, spectral centroid.
    No output file is produced — results are returned as JSON only.
    """
    task_id  = uuid.uuid4().hex
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True)

    suffix     = Path(safe_name(file.filename)).suffix.lower() or ".wav"
    input_path = task_dir / f"input{suffix}"
    input_path.write_bytes(await file.read())

    try:
        result = await run_in_thread(analyze_audio, input_path)
    except Exception as exc:
        raise HTTPException(500, str(exc))

    return {
        "task_id":  task_id,
        "filename": safe_name(file.filename),
        **result,
    }
