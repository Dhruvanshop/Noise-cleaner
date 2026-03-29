"""
/api/batch        — POST: enqueue multi-file batch job, returns {job_id}
/api/batch/download/{job_id} — GET: download ZIP of all processed files

Supported tools: denoise, normalize, trim, convert, repair, dereverberate
"""
from __future__ import annotations

import asyncio
import io
import json
import uuid
import zipfile
from pathlib import Path
from typing import List

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from ..config import TEMP_DIR, executor
from ..jobs import registry
from .deps import safe_name

router = APIRouter(tags=["batch"])


# ── helpers ───────────────────────────────────────────────────────────────────

def _process_one(tool: str, input_path: Path, out_dir: Path, params: dict) -> Path:
    """
    Synchronously process a single file with *tool*.
    Returns the path to the output file.
    Raises on error.
    """
    fmt = params.get("output_format", "wav")
    out_path = out_dir / f"output.{fmt}"

    if tool == "denoise":
        from ..denoise import DenoiseConfig, denoise_file
        cfg = DenoiseConfig(
            strength=float(params.get("strength", 0.85)),
            prop_decrease=float(params.get("prop_decrease", 0.85)),
        )
        res = denoise_file(input_path, out_path, cfg, output_format=fmt)
        if not res["ok"]:
            raise RuntimeError(res.get("error", "denoise failed"))

    elif tool == "normalize":
        from ..normalize import normalize_file
        res = normalize_file(
            input_path, out_path,
            target_lufs=float(params.get("target_lufs", -16.0)),
            true_peak_ceiling=float(params.get("true_peak_ceiling", -1.0)),
            output_format=fmt,
        )
        if not res["ok"]:
            raise RuntimeError(res.get("error", "normalize failed"))

    elif tool == "trim":
        from ..trim import trim_file
        res = trim_file(
            input_path, out_path,
            threshold_db=float(params.get("threshold_db", -40.0)),
            min_silence_ms=int(params.get("min_silence_ms", 500)),
            padding_ms=int(params.get("padding_ms", 50)),
            output_format=fmt,
        )
        if not res.get("ok"):
            raise RuntimeError(res.get("error", "trim failed"))

    elif tool == "convert":
        from ..converter import convert_file
        convert_file(
            input_path, out_path,
            output_format=fmt,
            bitrate=params.get("bitrate", "192k"),
            sample_rate=int(params.get("sample_rate", 44100)),
        )

    elif tool == "repair":
        from ..repair import repair_audio
        result = repair_audio(
            input_path, out_dir,
            remove_hum_flag=bool(params.get("remove_hum", True)),
            hum_freq=int(params.get("hum_freq", 0)),
            hum_harmonics=int(params.get("hum_harmonics", 4)),
            hum_strength=float(params.get("hum_strength", 1.0)),
            remove_clicks=bool(params.get("remove_clicks", True)),
            click_threshold=float(params.get("click_threshold", 6.0)),
            output_format=fmt,
        )
        src = Path(result["_out_path"])
        src.rename(out_path)

    elif tool == "dereverberate":
        from ..dereverberate import dereverberate_audio
        result = dereverberate_audio(
            input_path, out_dir,
            strength=float(params.get("strength", 0.7)),
            decay_ms=float(params.get("decay_ms", 80.0)),
            output_format=fmt,
        )
        src = Path(result["_out_path"])
        src.rename(out_path)

    else:
        raise ValueError(f"Unknown tool: {tool!r}")

    return out_path


def _blocking_batch(job_id: str, files_data: list[tuple[str, bytes]], tool: str, params: dict) -> None:
    """Runs entirely in the thread pool — processes every file then zips results."""
    registry.mark_processing(job_id)
    job_dir = TEMP_DIR / job_id
    results = []
    errors  = []

    for idx, (orig_name, data) in enumerate(files_data):
        item_dir = job_dir / f"file_{idx:04d}"
        item_dir.mkdir(parents=True, exist_ok=True)

        suffix     = Path(safe_name(orig_name)).suffix.lower() or ".wav"
        input_path = item_dir / f"input{suffix}"
        input_path.write_bytes(data)

        try:
            out_path = _process_one(tool, input_path, item_dir, params)
            results.append((orig_name, out_path))
        except Exception as exc:
            errors.append({"file": orig_name, "error": str(exc)})

    # Build ZIP
    zip_path = job_dir / "batch_results.zip"
    fmt = params.get("output_format", "wav")
    with zipfile.ZipFile(str(zip_path), "w", zipfile.ZIP_DEFLATED) as zf:
        for orig_name, out_path in results:
            stem = Path(orig_name).stem
            zf.write(str(out_path), f"{stem}_processed.{fmt}")

    registry.mark_done(job_id, {
        "zip_path":    str(zip_path),
        "files_ok":    len(results),
        "files_error": len(errors),
        "errors":      errors,
    })


# ── endpoints ─────────────────────────────────────────────────────────────────

@router.post("/batch")
async def api_batch(
    background_tasks: BackgroundTasks,
    files:         List[UploadFile] = File(...),
    tool:          str              = Form("denoise"),
    params:        str              = Form("{}"),   # JSON-encoded tool params
):
    """
    Enqueue a batch job.  Returns ``{"job_id": "…"}`` immediately.
    Poll ``GET /api/jobs/{job_id}`` until done, then download the ZIP via
    ``GET /api/batch/download/{job_id}``.
    """
    if not files:
        raise HTTPException(422, "At least one file is required")

    try:
        params_dict = json.loads(params) if params else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(422, f"Invalid params JSON: {exc}")

    # Read all files eagerly before returning
    files_data = [(safe_name(f.filename), await f.read()) for f in files]

    job_id  = uuid.uuid4().hex
    job_dir = TEMP_DIR / job_id
    job_dir.mkdir(parents=True)

    registry.create(job_id, tool=tool, file_count=len(files_data))

    async def _run():
        import asyncio as _aio
        loop = _aio.get_event_loop()
        await loop.run_in_executor(
            executor,
            lambda: _blocking_batch(job_id, files_data, tool, params_dict),
        )

    background_tasks.add_task(_run)

    return {"job_id": job_id, "file_count": len(files_data), "tool": tool}


@router.get("/batch/download/{job_id}")
async def api_batch_download(job_id: str):
    """Download the ZIP archive of processed files for a completed batch job."""
    job = registry.get(job_id)
    if job is None:
        raise HTTPException(404, "Batch job not found or expired")
    if job["status"] != "done":
        raise HTTPException(409, f"Batch job status is '{job['status']}' — not yet complete")

    zip_path = Path(job["result"]["zip_path"])
    if not zip_path.exists():
        raise HTTPException(404, "Result ZIP not found — may have been cleaned up")

    return FileResponse(
        str(zip_path),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="batch_results.zip"'},
    )
