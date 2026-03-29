"""/api/video/* — video denoising + stream/download."""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import TEMP_DIR
from ..denoise_ai import _AI_AVAILABLE
from ..video import _FFMPEG_AVAILABLE, denoise_video_file
from .deps import run_in_thread, safe_name

router = APIRouter(tags=["video"])


@router.post("/video/denoise")
async def api_video_denoise(
    file:    UploadFile = File(...),
    backend: str        = Form("auto"),
):
    if not _FFMPEG_AVAILABLE:
        raise HTTPException(500, "ffmpeg not installed")

    task_id  = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True)

    suffix     = Path(safe_name(file.filename)).suffix.lower() or ".mp4"
    input_path = task_dir / f"input{suffix}"
    input_path.write_bytes(await file.read())

    use_ai      = (backend == "ai") or (backend == "auto" and _AI_AVAILABLE)
    output_path = task_dir / "output.mp4"

    try:
        result = await run_in_thread(
            denoise_video_file, input_path, output_path, task_dir, use_ai=use_ai
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    if not result.get("ok"):
        raise HTTPException(500, result.get("error", "Video denoising failed"))

    (task_dir / ".tool").write_text("video")
    return {
        "task_id":         task_id,
        "filename":        safe_name(file.filename),
        "duration":        result.get("duration"),
        "width":           result.get("width"),
        "height":          result.get("height"),
        "fps":             result.get("fps"),
        "video_codec":     result.get("video_codec"),
        "input_size":      input_path.stat().st_size,
        "output_size":     output_path.stat().st_size,
        "download_url":    f"/api/video/download/{task_id}",
        "stream_url":      f"/api/video/stream/{task_id}",
    }


@router.get("/video/download/{task_id}")
async def api_video_download(task_id: str):
    path = TEMP_DIR / task_id / "output.mp4"
    if not path.exists():
        raise HTTPException(404, "Video not found")
    return FileResponse(
        str(path), media_type="video/mp4",
        headers={"Content-Disposition": 'attachment; filename="denoised_video.mp4"'},
    )


@router.get("/video/stream/{task_id}")
async def api_video_stream(task_id: str):
    path = TEMP_DIR / task_id / "output.mp4"
    if not path.exists():
        raise HTTPException(404, "Video not found")
    return FileResponse(str(path), media_type="video/mp4")
