"""/api/caption/* — generate SRT, convert to VTT, burn captions into video."""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..caption import burn_captions, get_available_fonts, srt_to_vtt
from ..config import TEMP_DIR
from ..transcribe import _WHISPER_AVAILABLE, transcribe_file
from .deps import run_in_thread, safe_name

router = APIRouter(tags=["caption"])


# ── fonts ──────────────────────────────────────────────────────────────────────

@router.get("/fonts")
async def api_fonts():
    return {"fonts": get_available_fonts()}


# ── generate SRT via Whisper ───────────────────────────────────────────────────

@router.post("/caption/generate_srt")
async def api_caption_generate_srt(
    file:       UploadFile | None = File(None),
    task_id:    str               = Form(""),
    model_size: str               = Form("base"),
    language:   str               = Form(""),
):
    if not _WHISPER_AVAILABLE:
        raise HTTPException(503, "Whisper not installed — run: pip install openai-whisper")

    if task_id:
        task_dir   = TEMP_DIR / task_id
        candidates = list(task_dir.glob("output.mp4")) + list(task_dir.glob("input.*"))
        if not candidates:
            raise HTTPException(404, "Task not found")
        input_path = candidates[0]
        out_dir    = task_dir / "transcript"
    elif file is not None:
        new_id     = str(uuid.uuid4())
        task_dir   = TEMP_DIR / new_id
        task_dir.mkdir(parents=True)
        suffix     = Path(safe_name(file.filename)).suffix.lower() or ".wav"
        input_path = task_dir / f"input{suffix}"
        input_path.write_bytes(await file.read())
        out_dir    = task_dir / "transcript"
        task_id    = new_id
    else:
        raise HTTPException(400, "Provide 'file' or 'task_id'")

    try:
        result = await run_in_thread(
            transcribe_file, input_path, out_dir,
            model_size=model_size, language=language or None, task="transcribe",
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    if not result.get("ok"):
        raise HTTPException(500, result.get("error", "Transcription failed"))

    srt_path = out_dir / "transcript.srt"
    srt_text = srt_path.read_text(encoding="utf-8") if srt_path.exists() else ""
    return {"task_id": task_id, "language": result.get("language", ""), "srt": srt_text, "text": result.get("text", "")}


# ── SRT → VTT ─────────────────────────────────────────────────────────────────

@router.post("/caption/srt_to_vtt")
async def api_srt_to_vtt(srt: str = Form(...)):
    return {"vtt": srt_to_vtt(srt)}


# ── burn captions ─────────────────────────────────────────────────────────────

@router.post("/caption/burn")
async def api_caption_burn(
    file:          UploadFile | None = File(None),
    video_task_id: str               = Form(""),
    srt_text:      str               = Form(...),
    font_name:     str               = Form("Arial"),
    font_size:     int               = Form(24),
    primary_color: str               = Form("#FFFFFF"),
    outline_color: str               = Form("#000000"),
    position:      str               = Form("bottom"),
    bold:          bool              = Form(False),
    italic:        bool              = Form(False),
    outline:       int               = Form(2),
    box:           bool              = Form(False),
):
    task_id  = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True)

    if video_task_id:
        src = TEMP_DIR / video_task_id / "output.mp4"
        if not src.exists():
            candidates = list((TEMP_DIR / video_task_id).glob("input.*"))
            if not candidates:
                raise HTTPException(404, "Source video task not found")
            src = candidates[0]
        input_path = task_dir / f"input{src.suffix}"
        shutil.copy2(src, input_path)
    elif file is not None:
        suffix     = Path(safe_name(file.filename)).suffix.lower() or ".mp4"
        input_path = task_dir / f"input{suffix}"
        input_path.write_bytes(await file.read())
    else:
        raise HTTPException(400, "Provide 'file' or 'video_task_id'")

    srt_path    = task_dir / "captions.srt"
    srt_path.write_text(srt_text, encoding="utf-8")
    output_path = task_dir / "captioned.mp4"

    try:
        result = await run_in_thread(
            burn_captions, input_path, srt_path, output_path,
            font_name=font_name, font_size=font_size,
            primary_color=primary_color, outline_color=outline_color,
            position=position, bold=bold, italic=italic,
            outline=outline, box=box,
        )
    except Exception as exc:
        raise HTTPException(500, str(exc))

    if not result.get("ok"):
        raise HTTPException(500, result.get("error", "Caption burn failed"))

    (task_dir / ".tool").write_text("caption")
    return {
        "task_id":      task_id,
        "download_url": f"/api/caption/download/{task_id}",
        "stream_url":   f"/api/caption/stream/{task_id}",
    }


@router.get("/caption/download/{task_id}")
async def api_caption_download(task_id: str):
    path = TEMP_DIR / task_id / "captioned.mp4"
    if not path.exists():
        raise HTTPException(404, "Captioned video not found")
    return FileResponse(
        str(path), media_type="video/mp4",
        headers={"Content-Disposition": 'attachment; filename="captioned_video.mp4"'},
    )


@router.get("/caption/stream/{task_id}")
async def api_caption_stream(task_id: str):
    path = TEMP_DIR / task_id / "captioned.mp4"
    if not path.exists():
        raise HTTPException(404, "Captioned video not found")
    return FileResponse(str(path), media_type="video/mp4")
