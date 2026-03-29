"""
Audio loudness normalization using pyloudnorm (ITU-R BS.1770).

Standards:
  -14 LUFS  →  Spotify / Apple Music / YouTube streaming
  -16 LUFS  →  Podcast standard (AES / Spotify Podcasts)
  -23 LUFS  →  Broadcast (EBU R128)
  -9  LUFS  →  TikTok / Instagram Reels
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

try:
    import pyloudnorm as pyln
    _PYLN_OK = True
except ImportError:
    _PYLN_OK = False


def measure_loudness(audio: np.ndarray, sr: int) -> dict:
    """Return integrated LUFS, true-peak dBFS, and dynamic range."""
    if not _PYLN_OK:
        return {"lufs": None, "true_peak_db": None, "dynamic_range_db": None}

    meter = pyln.Meter(sr)
    lufs = float(meter.integrated_loudness(audio))

    # True peak (per channel, take max)
    tp = float(np.max(np.abs(audio)))
    tp_db = 20.0 * np.log10(tp + 1e-12)

    # Dynamic range: std-dev of per-second RMS in dB
    hop = sr
    rms_vals = []
    for i in range(0, len(audio) - hop, hop):
        chunk = audio[i : i + hop]
        rms = float(np.sqrt(np.mean(chunk.astype(np.float64) ** 2)))
        if rms > 1e-10:
            rms_vals.append(20.0 * np.log10(rms))
    dr = float(np.ptp(rms_vals)) if len(rms_vals) >= 2 else 0.0

    return {
        "lufs":            round(lufs, 1),
        "true_peak_db":    round(tp_db, 1),
        "dynamic_range_db": round(dr, 1),
    }


def normalize_file(
    input_path:  str | Path,
    output_path: str | Path,
    target_lufs: float = -16.0,
    true_peak_ceiling: float = -1.0,  # dBFS
    output_format: str = "wav",
) -> dict:
    """
    Normalize integrated loudness to target_lufs, then clip to true_peak_ceiling.

    Returns metadata dict.
    """
    if not _PYLN_OK:
        return {"ok": False, "error": "pyloudnorm not installed"}

    input_path  = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio, sr = sf.read(str(input_path), always_2d=True)
    audio = audio.astype(np.float64)

    meter = pyln.Meter(sr)
    lufs_in = float(meter.integrated_loudness(audio))

    if not np.isfinite(lufs_in) or lufs_in < -70:
        # Too quiet to measure — just copy through
        audio_out = audio.astype(np.float32)
        lufs_out = lufs_in
    else:
        audio_out = pyln.normalize.loudness(audio, lufs_in, target_lufs)

        # True-peak ceiling
        ceiling_lin = 10 ** (true_peak_ceiling / 20.0)
        peak = float(np.max(np.abs(audio_out)))
        if peak > ceiling_lin:
            audio_out *= ceiling_lin / peak

        audio_out = audio_out.astype(np.float32)
        lufs_out  = float(meter.integrated_loudness(audio_out.astype(np.float64)))

    _write_audio(audio_out, sr, output_path, output_format)

    return {
        "ok":           True,
        "lufs_in":      round(lufs_in, 1),
        "lufs_out":     round(lufs_out, 1),
        "true_peak_db": round(20.0 * np.log10(float(np.max(np.abs(audio_out))) + 1e-12), 1),
        "gain_db":      round(lufs_out - lufs_in, 1),
    }


def _write_audio(audio: np.ndarray, sr: int, path: Path, fmt: str) -> None:
    fmt = fmt.lower()
    if fmt in ("wav", "flac", "ogg"):
        sf.write(str(path), audio, sr)
    elif fmt == "mp3":
        _write_mp3(audio, sr, path)
    elif fmt in ("m4a", "aac"):
        _write_ffmpeg(audio, sr, path, "m4a")
    else:
        sf.write(str(path), audio, sr)


def _write_mp3(audio: np.ndarray, sr: int, path: Path, bitrate: int = 192) -> None:
    from pydub import AudioSegment
    import io, struct
    # soundfile → wav bytes → pydub → mp3
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    buf.seek(0)
    seg = AudioSegment.from_wav(buf)
    seg.export(str(path), format="mp3", bitrate=f"{bitrate}k")


def _write_ffmpeg(audio: np.ndarray, sr: int, path: Path, fmt: str) -> None:
    import io
    from pydub import AudioSegment
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    buf.seek(0)
    seg = AudioSegment.from_wav(buf)
    seg.export(str(path), format=fmt)
