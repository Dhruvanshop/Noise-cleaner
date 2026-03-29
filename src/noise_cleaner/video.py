"""
video.py — Video noise removal pipeline.

Workflow:
  1. ffprobe  — read video metadata (resolution, fps, codecs, duration)
  2. ffmpeg   — extract audio track → WAV
  3. Denoise  — run existing DNS-64 AI or Wiener algorithm on the WAV
  4. ffmpeg   — remux clean audio back into original video container
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

_FFMPEG  = shutil.which("ffmpeg")
_FFPROBE = shutil.which("ffprobe")
_FFMPEG_AVAILABLE = _FFMPEG is not None


# ─────────────────────────────────────────────────── helpers ─────

def get_video_info(video_path: Path) -> dict:
    """Return video/audio stream metadata via ffprobe."""
    if not _FFPROBE:
        return {"ok": False, "error": "ffprobe not found — install ffmpeg"}
    try:
        r = subprocess.run(
            [_FFPROBE, "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", str(video_path)],
            capture_output=True, text=True, timeout=30,
        )
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr[-400:]}

        data  = json.loads(r.stdout)
        vs    = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
        as_   = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), None)
        dur   = float(data.get("format", {}).get("duration", 0))

        info: dict = {
            "ok": True,
            "duration": round(dur, 2),
            "has_video": vs is not None,
            "has_audio": as_ is not None,
        }
        if vs:
            info["width"]       = vs.get("width", 0)
            info["height"]      = vs.get("height", 0)
            info["video_codec"] = vs.get("codec_name", "unknown")
            try:
                n, d = vs.get("r_frame_rate", "30/1").split("/")
                info["fps"] = round(int(n) / max(int(d), 1), 2)
            except Exception:
                info["fps"] = 0
        if as_:
            info["samplerate"]     = int(as_.get("sample_rate", 44100))
            info["audio_channels"] = as_.get("channels", 2)
            info["audio_codec"]    = as_.get("codec_name", "unknown")
        return info
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def extract_audio(video_path: Path, audio_path: Path, sample_rate: int = 44100) -> dict:
    """Extract audio from video to a WAV file."""
    if not _FFMPEG:
        return {"ok": False, "error": "ffmpeg not found"}
    try:
        r = subprocess.run(
            [_FFMPEG, "-y", "-i", str(video_path),
             "-vn", "-acodec", "pcm_s16le", "-ar", str(sample_rate), "-ac", "2",
             str(audio_path)],
            capture_output=True, text=True, timeout=600,
        )
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr[-500:]}
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def remux_audio(video_path: Path, audio_path: Path, output_path: Path) -> dict:
    """Replace audio track in video; copy video stream unchanged."""
    if not _FFMPEG:
        return {"ok": False, "error": "ffmpeg not found"}
    try:
        r = subprocess.run(
            [_FFMPEG, "-y",
             "-i", str(video_path),
             "-i", str(audio_path),
             "-c:v", "copy",
             "-c:a", "aac", "-b:a", "192k",
             "-map", "0:v:0", "-map", "1:a:0",
             "-shortest",
             str(output_path)],
            capture_output=True, text=True, timeout=1200,
        )
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr[-500:]}
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


# ─────────────────────────────────────────────────── pipeline ────

def denoise_video_file(
    input_path: Path,
    output_path: Path,
    task_dir: Path,
    use_ai: bool = True,
) -> dict:
    """
    Full video denoising pipeline:
      extract audio → AI/algorithm denoise → remux into MP4 output.

    Returns a dict with "ok" bool plus the video info fields from get_video_info().
    """
    from .denoise_ai import _AI_AVAILABLE, denoise_file_ai
    from .denoise    import DenoiseConfig, denoise_file

    # 1 ── Read video metadata ────────────────────────────────────
    info = get_video_info(input_path)
    if not info.get("ok"):
        return {"ok": False, "error": info.get("error", "Could not read video")}
    if not info.get("has_video"):
        return {"ok": False, "error": "File has no video stream"}

    # 2 ── Extract audio ──────────────────────────────────────────
    audio_path = task_dir / "extracted_audio.wav"
    sr = info.get("samplerate", 44100)

    if info.get("has_audio"):
        res = extract_audio(input_path, audio_path, sample_rate=sr)
        if not res["ok"]:
            return {"ok": False, "error": "Audio extraction failed: " + res.get("error", "")}
    else:
        # Video-only file → generate matching silent WAV for the remux step
        dur = info.get("duration", 1)
        subprocess.run(
            [_FFMPEG, "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
             "-t", str(dur), str(audio_path)],
            capture_output=True,
        )

    # 3 ── Denoise audio ──────────────────────────────────────────
    clean_path = task_dir / "clean_audio.wav"
    denoised = False
    if use_ai and _AI_AVAILABLE:
        ai_res = denoise_file_ai(audio_path, clean_path)
        if ai_res.get("ok"):
            denoised = True
    if not denoised:
        denoise_file(audio_path, clean_path, DenoiseConfig())

    # 4 ── Remux ─────────────────────────────────────────────────
    res = remux_audio(input_path, clean_path, output_path)
    if not res["ok"]:
        return {"ok": False, "error": "Remux failed: " + res.get("error", "")}

    return {"ok": True, **info}
