"""/api/trim — silence removal (audio & video)."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import TEMP_DIR
from ..trim import trim_silence
from ..video import _FFMPEG_AVAILABLE, extract_audio
from .deps import is_video, run_in_thread, safe_name

router = APIRouter(tags=["trim"])


@router.post("/trim")
async def api_trim(
    file:            UploadFile = File(...),
    min_silence_ms:  int        = Form(500),
    threshold_db:    float      = Form(-40.0),
    keep_padding_ms: int        = Form(80),
    output_format:   str        = Form("wav"),
):
    task_id  = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True)

    suffix     = Path(safe_name(file.filename)).suffix.lower() or ".wav"
    input_path = task_dir / f"input{suffix}"
    input_path.write_bytes(await file.read())

    fmt = output_format.lower()

    audio_in = input_path
    if is_video(input_path):
        if not _FFMPEG_AVAILABLE:
            raise HTTPException(500, "ffmpeg required for video files")
        extracted = task_dir / "audio_extracted.wav"
        res = await run_in_thread(extract_audio, input_path, extracted)
        if not res.get("ok"):
            raise HTTPException(500, res.get("error", "Audio extraction failed"))
        audio_in = extracted
        fmt = "wav"

    output_path = task_dir / f"output.{fmt}"

    try:
        result = await run_in_thread(
            trim_silence, audio_in, output_path,
            min_silence_ms=min_silence_ms,
            threshold_db=threshold_db,
            keep_padding_ms=keep_padding_ms,
            output_format=fmt,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    if not result["ok"]:
        raise HTTPException(500, result.get("error", "Trim failed"))

    (task_dir / ".output_fmt").write_text(fmt)
    (task_dir / ".tool").write_text("trim")

    return {
        "task_id":       task_id,
        "filename":      safe_name(file.filename),
        "input_size":    input_path.stat().st_size,
        "output_size":   output_path.stat().st_size,
        "output_format": fmt,
        **{k: v for k, v in result.items() if k != "ok"},
    }
