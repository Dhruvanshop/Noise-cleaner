"""/api/dereverberate — room reverb removal via spectral subtraction."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from ..config import TEMP_DIR
from ..dereverberate import dereverberate_audio
from .deps import run_in_thread, safe_name

router = APIRouter(tags=["dereverberate"])


@router.post("/dereverberate")
async def api_dereverberate(
    file:          UploadFile = File(...),
    strength:      float      = Form(0.7),   # 0.0 – 1.0
    decay_ms:      float      = Form(80.0),  # estimated room RT20
    output_format: str        = Form("wav"),
):
    """Remove room reverb from audio using STFT spectral subtraction."""
    task_id  = uuid.uuid4().hex
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True)

    suffix     = Path(safe_name(file.filename)).suffix.lower() or ".wav"
    input_path = task_dir / f"input{suffix}"
    input_path.write_bytes(await file.read())

    fmt = output_format.lower()

    try:
        result = await run_in_thread(
            dereverberate_audio, input_path, task_dir,
            strength=strength,
            decay_ms=decay_ms,
            output_format=fmt,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    # Rename to standard path for /api/download
    out_src = Path(result.pop("_out_path"))
    result.pop("task_id", None)   # discard backend UUID
    out_std = task_dir / f"output.{fmt}"
    out_src.rename(out_std)

    (task_dir / ".output_fmt").write_text(fmt)
    (task_dir / ".tool").write_text("dereverberate")

    return {
        "task_id":  task_id,
        "filename": safe_name(file.filename),
        **result,
    }
