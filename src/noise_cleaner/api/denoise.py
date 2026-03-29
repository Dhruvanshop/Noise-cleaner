"""
/api/capabilities  — feature detection
/api/denoise       — audio noise removal (algorithm + AI)
/api/audio/*       — playback & download helpers
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse

from ..config import TEMP_DIR, ENABLE_AI_DENOISE
from ..denoise import DenoiseConfig, DenoiseResult, _WEBRTCVAD_AVAILABLE, denoise_file
from ..denoise_ai import _AI_AVAILABLE, denoise_file_ai
from ..normalize import measure_loudness
from ..converter import convert_file
from .deps import run_in_thread, safe_name

router = APIRouter(tags=["denoise"])


# ── capabilities ──────────────────────────────────────────────────────────────

@router.get("/capabilities")
async def api_capabilities():
    """Return which optional features are available on this server."""
    from ..stem import _DEMUCS_AVAILABLE
    from ..transcribe import _WHISPER_AVAILABLE
    return {
        "webrtcvad": _WEBRTCVAD_AVAILABLE,
        "ai":        _AI_AVAILABLE and ENABLE_AI_DENOISE,
        "demucs":    _DEMUCS_AVAILABLE,
        "whisper":   _WHISPER_AVAILABLE,
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def _rms(audio: np.ndarray) -> float:
    return float(np.sqrt(np.mean(audio.astype(np.float64) ** 2)))


def _do_denoise(
    input_path: Path,
    output_path: Path,
    backend: str,
    cfg_kwargs: dict,
) -> tuple[str, DenoiseResult]:
    """Blocking denoise \u2014 runs inside the thread-pool."""
    # Respect ENABLE_AI_DENOISE config (commercial license compliance)
    use_ai = ENABLE_AI_DENOISE and ((backend == \"ai\") or (backend == \"auto\" and _AI_AVAILABLE))

    if use_ai:
        ai_res = denoise_file_ai(input_path, output_path)
        if ai_res["ok"]:
            return "dns64", DenoiseResult(
                output_path=output_path,
                vad_used=False,
                vad_engine="dns64",
                speech_fraction=0.0,
            )
        if backend == "ai":
            raise RuntimeError(f"AI denoising failed: {ai_res['error']}")
        # auto-fallback to algorithm

    dn = denoise_file(input_path, output_path, DenoiseConfig(**cfg_kwargs))
    return "algorithm", dn


# ── /api/denoise ──────────────────────────────────────────────────────────────

@router.post("/denoise")
async def api_denoise(
    file:                  UploadFile = File(...),
    backend:               str   = Form("auto"),
    output_format:         str   = Form("wav"),
    use_vad:               bool  = Form(True),
    vad_aggressiveness:    int   = Form(2),
    noise_frames_frac:     float = Form(0.15),
    n_std_thresh:          float = Form(1.5),
    noise_bias_correction: float = Form(1.25),
    prop_decrease:         float = Form(0.90),
    dd_alpha:              float = Form(0.98),
    gain_floor:            float = Form(0.08),
    gain_smooth_attack:    float = Form(0.40),
    gain_smooth_release:   float = Form(0.92),
    residual_sub_factor:   float = Form(0.10),
    n_passes:              int   = Form(1),
    n_fft:                 int   = Form(2048),
    hop_length:            int   = Form(512),
    win_length:            int   = Form(2048),
):
    task_id  = str(uuid.uuid4())
    task_dir = TEMP_DIR / task_id
    task_dir.mkdir(parents=True)

    suffix      = Path(safe_name(file.filename)).suffix.lower() or ".wav"
    input_path  = task_dir / f"input{suffix}"
    output_path = task_dir / "output.wav"
    input_path.write_bytes(await file.read())

    cfg_kwargs = dict(
        use_vad=use_vad, vad_aggressiveness=vad_aggressiveness,
        noise_frames_frac=noise_frames_frac, n_std_thresh=n_std_thresh,
        noise_bias_correction=noise_bias_correction,
        prop_decrease=prop_decrease, dd_alpha=dd_alpha, gain_floor=gain_floor,
        gain_smooth_attack=gain_smooth_attack, gain_smooth_release=gain_smooth_release,
        residual_sub_factor=residual_sub_factor, n_passes=n_passes,
        n_fft=n_fft, hop_length=hop_length, win_length=win_length,
    )

    t0 = time.perf_counter()
    try:
        used_backend, dn_result = await run_in_thread(
            _do_denoise, input_path, output_path, backend, cfg_kwargs
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    elapsed = round(time.perf_counter() - t0, 2)

    info      = sf.info(str(input_path))
    audio_in, _  = sf.read(str(input_path),  dtype="float32", always_2d=True)
    audio_out, _ = sf.read(str(output_path), dtype="float32", always_2d=True)

    rms_in, rms_out = _rms(audio_in), _rms(audio_out)
    noise_db = 0.0
    if rms_in > 1e-10 and rms_out > 1e-10:
        noise_db = round(20.0 * float(np.log10(rms_in / rms_out)), 1)

    loudness = measure_loudness(audio_out.astype(np.float64), info.samplerate)

    fmt = output_format.lower()
    final_path = output_path
    if fmt != "wav":
        ext      = {"mp3": "mp3", "flac": "flac", "ogg": "ogg", "m4a": "m4a"}.get(fmt, "wav")
        conv_path = output_path.parent / f"output.{ext}"
        res = convert_file(output_path, conv_path, output_format=fmt)
        if res["ok"]:
            final_path = conv_path
    (task_dir / ".output_fmt").write_text(fmt)

    vad_label = {"webrtcvad": "WebRTC VAD", "sfm": "Spectral VAD",
                 "min_stats": "Min-Stats"}.get(dn_result.vad_engine, dn_result.vad_engine)

    return {
        "task_id":            task_id,
        "filename":           safe_name(file.filename),
        "duration":           round(info.duration, 2),
        "samplerate":         info.samplerate,
        "channels":           info.channels,
        "input_size":         input_path.stat().st_size,
        "output_size":        final_path.stat().st_size,
        "output_format":      fmt,
        "processing_time":    elapsed,
        "noise_reduction_db": noise_db,
        "lufs_out":           loudness["lufs"],
        "true_peak_db":       loudness["true_peak_db"],
        "dynamic_range_db":   loudness["dynamic_range_db"],
        "backend":            used_backend,
        "vad_used":           dn_result.vad_used,
        "vad_engine":         dn_result.vad_engine,
        "vad_engine_label":   vad_label,
        "speech_fraction":    round(dn_result.speech_fraction, 3),
    }


# ── playback / download helpers ───────────────────────────────────────────────

@router.get("/audio/original/{task_id}")
async def audio_original(task_id: str):
    files = list((TEMP_DIR / task_id).glob("input.*"))
    if not files:
        raise HTTPException(404, "Not found")
    return FileResponse(str(files[0]))


@router.get("/audio/denoised/{task_id}")
async def audio_denoised(task_id: str):
    files = list((TEMP_DIR / task_id).glob("output.wav"))
    if not files:
        raise HTTPException(404, "Not found")
    return FileResponse(str(files[0]), media_type="audio/wav")


@router.get("/audio/output/{task_id}")
async def audio_output(task_id: str):
    """
    Serve the processed output file *inline* (no Content-Disposition attachment)
    so an HTML <audio> element can stream it directly for preview.
    Works for every tool that writes output.{fmt} + .output_fmt in its task dir.
    """
    task_dir = TEMP_DIR / task_id
    fmt_file = task_dir / ".output_fmt"
    fmt = fmt_file.read_text().strip() if fmt_file.exists() else "wav"
    ext = {"mp3": "mp3", "flac": "flac", "ogg": "ogg", "m4a": "m4a", "wav": "wav"}.get(fmt, "wav")
    files = list(task_dir.glob(f"output.{ext}")) or list(task_dir.glob("output.wav"))
    if not files:
        raise HTTPException(404, "Output file not found")
    mime = {
        "mp3": "audio/mpeg", "flac": "audio/flac",
        "ogg": "audio/ogg",  "m4a": "audio/mp4", "wav": "audio/wav",
    }.get(fmt, "audio/wav")
    return FileResponse(str(files[0]), media_type=mime)  # no attachment header → inline


@router.get("/download/{task_id}")
async def api_download(task_id: str):
    task_dir    = TEMP_DIR / task_id
    input_files = list(task_dir.glob("input.*"))

    fmt_file = task_dir / ".output_fmt"
    fmt = fmt_file.read_text().strip() if fmt_file.exists() else "wav"
    ext = {"mp3": "mp3", "flac": "flac", "ogg": "ogg", "m4a": "m4a", "wav": "wav"}.get(fmt, "wav")

    output_files = list(task_dir.glob(f"output.{ext}")) or list(task_dir.glob("output.wav"))
    if not output_files:
        raise HTTPException(404, "Not found")

    base = input_files[0].stem if input_files else "audio"
    mime = {"mp3": "audio/mpeg", "flac": "audio/flac",
            "ogg": "audio/ogg",  "m4a": "audio/mp4", "wav": "audio/wav"}.get(fmt, "audio/wav")
    # Use the tool name (written by each API handler) for the download filename
    tool_file = task_dir / ".tool"
    suffix = tool_file.read_text().strip() if tool_file.exists() else "processed"
    return FileResponse(
        str(output_files[0]), media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="{base}_{suffix}.{ext}"'},
    )
