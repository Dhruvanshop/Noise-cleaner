"""/api/repair — audio repair: hum removal + click/pop repair."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import TEMP_DIR
from ..repair import repair_audio
from .deps import run_in_thread, safe_name

router = APIRouter(tags=["repair"])

_MIME = {
    "mp3": "audio/mpeg", "flac": "audio/flac",
    "ogg": "audio/ogg",  "wav": "audio/wav",
}


@router.post("/repair")
async def api_repair(
    file:            UploadFile = File(...),
    remove_hum:      bool       = Form(True),
    hum_freq:        int        = Form(0),        # 0 = auto-detect
    hum_harmonics:   int        = Form(4),
    hum_strength:    float      = Form(1.0),
    remove_clicks:   bool       = Form(True),
    click_threshold: float      = Form(6.0),
    output_format:   str        = Form("wav"),
):
    """Repair audio: remove hum/buzz and fix click/pop artefacts."""
    task_id  = uuid.uuid4().hex
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True)

    suffix     = Path(safe_name(file.filename)).suffix.lower() or ".wav"
    input_path = task_dir / f"input{suffix}"
    input_path.write_bytes(await file.read())

    fmt = output_format.lower()

    try:
        result = await run_in_thread(
            repair_audio, input_path, task_dir,
            remove_hum_flag=remove_hum,
            hum_freq=hum_freq,
            hum_harmonics=hum_harmonics,
            hum_strength=hum_strength,
            remove_clicks=remove_clicks,
            click_threshold=click_threshold,
            output_format=fmt,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    # Rename to the standard "output.{ext}" that /api/download uses
    out_src = Path(result.pop("_out_path"))
    result.pop("task_id", None)   # discard backend's internal UUID — directory is keyed to task_id below
    out_std = task_dir / f"output.{fmt}"
    out_src.rename(out_std)

    (task_dir / ".output_fmt").write_text(fmt)
    (task_dir / ".tool").write_text("repair")

    return {
        "task_id":  task_id,      # API-level UUID == TEMP_DIR sub-directory
        "filename": safe_name(file.filename),
        **result,
    }
