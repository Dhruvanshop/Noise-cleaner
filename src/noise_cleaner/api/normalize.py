"""/api/normalize — loudness normalization (audio & video)."""
from __future__ import annotations

import uuid
from pathlib import Path

import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import TEMP_DIR
from ..normalize import normalize_file
from ..video import _FFMPEG_AVAILABLE, extract_audio
from .deps import is_video, run_in_thread, safe_name

router = APIRouter(tags=["normalize"])


@router.post("/normalize")
async def api_normalize(
    file:              UploadFile = File(...),
    target_lufs:       float      = Form(-16.0),
    true_peak_ceiling: float      = Form(-1.0),
    output_format:     str        = Form("wav"),
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
            normalize_file, audio_in, output_path,
            target_lufs=target_lufs,
            true_peak_ceiling=true_peak_ceiling,
            output_format=fmt,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    if not result["ok"]:
        raise HTTPException(500, result.get("error", "Normalization failed"))

    (task_dir / ".output_fmt").write_text(fmt)
    (task_dir / ".tool").write_text("normalize")

    info = sf.info(str(audio_in))
    return {
        "task_id":         task_id,
        "filename":        safe_name(file.filename),
        "duration":        round(info.duration, 2),
        "samplerate":      info.samplerate,
        "channels":        info.channels,
        "input_size":      input_path.stat().st_size,
        "output_size":     output_path.stat().st_size,
        "output_format":   fmt,
        **{k: v for k, v in result.items() if k != "ok"},
    }
