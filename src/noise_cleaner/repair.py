"""
Audio repair — hum/buzz removal (notch filter) and click/pop detection + repair.
Pure scipy/numpy — no extra licensed dependencies.
"""
from __future__ import annotations

import io
import time
import uuid
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.ndimage import binary_dilation


# ── Hum detection ────────────────────────────────────────────────────────────

def _detect_hum_freq(data: np.ndarray, sr: int) -> int:
    """Auto-detect 50 or 60 Hz hum by comparing spectral energy at both."""
    mono = data.mean(axis=1) if data.ndim > 1 else data
    freqs = np.fft.rfftfreq(len(mono), 1 / sr)
    mag   = np.abs(np.fft.rfft(mono))

    def _band(fc: int) -> float:
        mask = (freqs >= fc - 3) & (freqs <= fc + 3)
        return float(mag[mask].sum())

    e50 = _band(50) + _band(100) + _band(150)
    e60 = _band(60) + _band(120) + _band(180)
    return 50 if e50 >= e60 else 60


def _notch(data: np.ndarray, sr: int, freq: float, Q: float = 35.0) -> np.ndarray:
    """Apply IIR notch filter at `freq` Hz."""
    b, a = signal.iirnotch(freq, Q, sr)
    if data.ndim == 1:
        return signal.filtfilt(b, a, data).astype(data.dtype)
    return np.column_stack(
        [signal.filtfilt(b, a, data[:, ch]) for ch in range(data.shape[1])]
    ).astype(data.dtype)


def remove_hum(
    data: np.ndarray,
    sr: int,
    hum_freq: int = 0,
    harmonics: int = 4,
    strength: float = 1.0,
) -> tuple[np.ndarray, int]:
    """
    Remove hum at fundamental frequency and harmonics.
    Returns (cleaned, detected_freq).
    """
    if hum_freq == 0:
        hum_freq = _detect_hum_freq(data, sr)

    Q = max(10.0, 20.0 + strength * 30.0)   # stronger Q = narrower notch
    result = data.copy()
    for h in range(1, harmonics + 1):
        freq = hum_freq * h
        if freq >= sr / 2 - 1:
            break
        notched = _notch(result, sr, float(freq), Q)
        result   = data * (1 - strength) + notched * strength
        data     = result
    return result, hum_freq


# ── Click / pop detection ─────────────────────────────────────────────────────

def _detect_clicks(
    data: np.ndarray,
    sr: int,
    threshold_sigma: float = 6.0,
    window_ms: float = 2.0,
) -> np.ndarray:
    """Return boolean mask where clicks are detected."""
    mono = data.mean(axis=1) if data.ndim > 1 else data.copy()
    win  = max(1, int(sr * window_ms / 1000))

    sq      = mono ** 2
    kernel  = np.ones(win) / win
    loc_rms = np.sqrt(np.convolve(sq, kernel, mode="same") + 1e-12)
    norm    = np.abs(mono) / (loc_rms + 1e-9)

    clicks = norm > threshold_sigma
    clicks = binary_dilation(clicks, iterations=max(1, win // 4))
    return clicks


def _repair_clicks(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Linear-interpolate over detected click regions."""

    def _repair_ch(ch: np.ndarray) -> np.ndarray:
        out = ch.copy()
        n   = len(mask)
        i   = 0
        while i < n:
            if mask[i]:
                start = i
                while i < n and mask[i]:
                    i += 1
                end     = i
                pre_v   = out[max(0, start - 1)]
                post_v  = out[min(n - 1, end)]
                length  = end - start
                for j in range(length):
                    t = (j + 1) / (length + 1)
                    out[start + j] = pre_v * (1 - t) + post_v * t
            else:
                i += 1
        return out

    result = data.copy()
    if result.ndim == 1:
        return _repair_ch(result)
    for ch in range(result.shape[1]):
        result[:, ch] = _repair_ch(result[:, ch])
    return result


# ── Public API ────────────────────────────────────────────────────────────────

def repair_audio(
    input_path: Path,
    output_dir: Path,
    *,
    remove_hum_flag: bool = True,
    hum_freq: int = 0,
    hum_harmonics: int = 4,
    hum_strength: float = 1.0,
    remove_clicks: bool = True,
    click_threshold: float = 6.0,
    output_format: str = "wav",
) -> dict:
    """
    Repair audio: hum removal + click interpolation.
    Returns metadata dict (does NOT include output_path key — caller pops it).
    """
    t0    = time.perf_counter()
    data, sr = sf.read(str(input_path), always_2d=False)
    orig_rms = float(np.sqrt(np.mean(data ** 2)) + 1e-12)

    result          = data.copy()
    detected_hum    = None
    clicks_repaired = 0

    if remove_hum_flag and hum_strength > 0:
        result, detected_hum = remove_hum(result, sr, hum_freq, hum_harmonics, hum_strength)

    if remove_clicks:
        mask            = _detect_clicks(result, sr, click_threshold)
        clicks_repaired = int(mask.sum())
        if clicks_repaired > 0:
            result = _repair_clicks(result, mask)

    # Prevent clipping
    peak = np.max(np.abs(result))
    if peak > 0.999:
        result = result / peak * 0.999

    task_id = uuid.uuid4().hex
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"repaired_{task_id[:8]}.{output_format}"
    _write(result, sr, out_path, output_format)

    new_rms = float(np.sqrt(np.mean(result ** 2)) + 1e-12)
    return {
        "task_id":          task_id,
        "_out_path":        str(out_path),        # internal — router pops this
        "output_format":    output_format,
        "duration":         round(len(data) / sr, 2),
        "samplerate":       sr,
        "channels":         1 if data.ndim == 1 else data.shape[1],
        "hum_freq_hz":      detected_hum,
        "clicks_repaired":  clicks_repaired,
        "rms_before_db":    round(20 * np.log10(orig_rms), 2),
        "rms_after_db":     round(20 * np.log10(new_rms), 2),
        "processing_time":  round(time.perf_counter() - t0, 2),
    }


def _write(audio: np.ndarray, sr: int, path: Path, fmt: str) -> None:
    if fmt in ("wav", "flac", "ogg"):
        sf.write(str(path), audio, sr, format=fmt.upper())
    else:
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        buf.seek(0)
        from pydub import AudioSegment
        seg = AudioSegment.from_wav(buf)
        seg.export(str(path), format="mp3" if fmt == "mp3" else "mp4")
