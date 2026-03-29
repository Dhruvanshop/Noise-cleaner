"""/api/remix — mix stems from a completed stems job with custom volumes."""
from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import TEMP_DIR
from ..remixer import remix_stems
from .deps import run_in_thread

router = APIRouter(tags=["remix"])

_MIME = {
    "mp3": "audio/mpeg", "flac": "audio/flac",
    "ogg": "audio/ogg",  "wav": "audio/wav",
}


@router.post("/remix")
async def api_remix(
    stems_job_id:  str   = Form(...),
    volumes:       str   = Form("{}"),   # JSON: {"vocals": 1.0, "drums": 0.8}
    muted:         str   = Form("[]"),   # JSON: ["bass", "other"]
    output_format: str   = Form("wav"),
    normalize:     bool  = Form(True),
):
    """
    Mix stems from a completed stems job.

    ``stems_job_id`` must be the ``job_id`` returned by ``POST /api/stems``
    after it finishes (status = done).
    """
    stems_dir = TEMP_DIR / stems_job_id / "stems"
    if not stems_dir.exists():
        raise HTTPException(
            404,
            "Stems job not found or not yet complete. "
            "Check /api/jobs/{stems_job_id} is status=done first.",
        )

    try:
        vols  = json.loads(volumes) if volumes else {}
        mutes = set(json.loads(muted)) if muted else set()
    except json.JSONDecodeError as exc:
        raise HTTPException(422, f"Invalid volumes/muted JSON: {exc}")

    task_id  = uuid.uuid4().hex
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True)

    fmt = output_format.lower()

    try:
        result = await run_in_thread(
            remix_stems, stems_dir, task_dir,
            volumes=vols,
            muted=mutes,
            output_format=fmt,
            normalize=normalize,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    # Rename to standard path so /api/download/{task_id} works
    out_src = Path(result.pop("_out_path"))
    result.pop("task_id", None)   # discard backend UUID
    out_std = task_dir / f"output.{fmt}"
    out_src.rename(out_std)

    (task_dir / ".output_fmt").write_text(fmt)
    (task_dir / ".tool").write_text("remix")

    return {"task_id": task_id, **result}


@router.get("/remix/stems_info/{stems_job_id}")
async def api_remix_stems_info(stems_job_id: str):
    """
    Return the list of stem names available for a completed stems job.
    Useful so the remix UI can dynamically build sliders.
    """
    stems_dir = TEMP_DIR / stems_job_id / "stems"
    if not stems_dir.exists():
        raise HTTPException(404, "Stems job not found or stems not yet ready")
    stems = sorted(p.stem for p in stems_dir.glob("*.wav"))
    return {"stems_job_id": stems_job_id, "stems": stems}
