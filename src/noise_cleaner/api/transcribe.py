"""/api/transcribe — Whisper speech-to-text."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import TEMP_DIR
from ..transcribe import _WHISPER_AVAILABLE, transcribe_file
from .deps import run_in_thread, safe_name

router = APIRouter(tags=["transcribe"])


@router.post("/transcribe")
async def api_transcribe(
    file:       UploadFile | None = File(None),
    task_id:    str               = Form(""),
    model_size: str               = Form("base"),
    language:   str               = Form(""),
    task_type:  str               = Form("transcribe"),
):
    if task_id:
        task_dir   = TEMP_DIR / task_id
        candidates = list(task_dir.glob("output.*")) + list(task_dir.glob("input.*"))
        if not candidates:
            raise HTTPException(404, "Task not found")
        input_path = candidates[0]
    elif file is not None:
        task_id    = str(uuid.uuid4())
        task_dir   = TEMP_DIR / task_id
        task_dir.mkdir(parents=True)
        suffix     = Path(safe_name(file.filename)).suffix.lower() or ".wav"
        input_path = task_dir / f"input{suffix}"
        input_path.write_bytes(await file.read())
    else:
        raise HTTPException(400, "Provide either 'file' or 'task_id'")

    try:
        result = await run_in_thread(
            transcribe_file, input_path,
            task_dir / "transcript",
            model_size=model_size,
            language=language or None,
            task=task_type,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    if not result["ok"]:
        raise HTTPException(500, result.get("error", "Transcription failed"))

    return {
        "task_id":         task_id,
        "language":        result.get("language", ""),
        "text":            result.get("text", ""),
        "segments":        result.get("segments", []),
        "txt_url":         f"/api/transcript_download/{task_id}/txt",
        "srt_url":         f"/api/transcript_download/{task_id}/srt",
        "json_url":        f"/api/transcript_download/{task_id}/json",
    }


@router.get("/transcript_download/{task_id}/{fmt}")
async def transcript_download(task_id: str, fmt: str):
    files = {"txt": "transcript.txt", "srt": "transcript.srt", "json": "transcript.json"}
    if fmt not in files:
        raise HTTPException(400, "Unknown format")
    path = TEMP_DIR / task_id / "transcript" / files[fmt]
    if not path.exists():
        raise HTTPException(404, "Transcript not found")
    mimes = {"txt": "text/plain", "srt": "text/plain", "json": "application/json"}
    return FileResponse(
        str(path), media_type=mimes[fmt],
        headers={"Content-Disposition": f'attachment; filename="transcript.{fmt}"'},
    )
