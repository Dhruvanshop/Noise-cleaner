"""
Audio analysis — BPM, musical key, loudness, spectral stats.

Uses librosa when available; falls back to pure numpy/scipy implementations.
All fallback code is MIT/BSD-compatible (numpy, scipy).
"""
from __future__ import annotations

import time
import warnings
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    import librosa
    _LIBROSA = True
except ImportError:
    _LIBROSA = False

# ── Constants ─────────────────────────────────────────────────────────────────
_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Krumhansl-Kessler tonal profiles (major / minor)
_MAJOR = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])


# ── Fallback BPM (autocorrelation) ───────────────────────────────────────────

def _bpm_numpy(mono: np.ndarray, sr: int) -> float:
    hop = 512
    frames = [mono[i : i + 1024] for i in range(0, len(mono) - 1024, hop)]
    if not frames:
        return 120.0
    energies = np.array([np.sqrt(np.mean(f ** 2)) for f in frames])
    corr     = np.correlate(energies, energies, mode="full")[len(energies) - 1 :]
    fps      = sr / hop
    lo, hi   = int(fps * 60 / 200), int(fps * 60 / 60)
    hi       = min(hi, len(corr) - 1)
    if lo >= hi:
        return 120.0
    peak_lag = np.argmax(corr[lo:hi]) + lo
    return round(float(fps * 60 / peak_lag), 1)


# ── Fallback key detection (chroma profile correlation) ──────────────────────

def _key_numpy(mono: np.ndarray, sr: int) -> tuple[str, str]:
    n_fft = min(8192, 2 ** int(np.log2(len(mono))))
    data  = mono[: min(len(mono), sr * 60)]   # use up to 60 s
    mag   = np.abs(np.fft.rfft(data, n=n_fft))
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)

    chroma = np.zeros(12)
    a4     = 440.0
    for i, f in enumerate(freqs[1:], 1):   # skip DC
        if f < 20 or f > 8000:
            continue
        pc = int(round(12 * np.log2(f / a4 + 1e-10))) % 12
        chroma[pc] += mag[i]

    total = chroma.sum()
    if total == 0:
        return "C", "major"
    chroma /= total

    best_s, best_root, best_mode = -np.inf, 0, "major"
    for root in range(12):
        shifted = np.roll(chroma, -root)
        maj_s   = float(np.corrcoef(shifted, _MAJOR / _MAJOR.sum())[0, 1])
        min_s   = float(np.corrcoef(shifted, _MINOR / _MINOR.sum())[0, 1])
        if maj_s > best_s:
            best_s, best_root, best_mode = maj_s, root, "major"
        if min_s > best_s:
            best_s, best_root, best_mode = min_s, root, "minor"
    return _NOTE_NAMES[best_root], best_mode


# ── Dynamic range ─────────────────────────────────────────────────────────────

def _dynamic_range(mono: np.ndarray, sr: int) -> float:
    hop = 1024
    rms_frames = [
        float(np.sqrt(np.mean(mono[i : i + hop] ** 2)))
        for i in range(0, len(mono) - hop, hop)
    ]
    if len(rms_frames) < 4:
        return 0.0
    p95 = np.percentile(rms_frames, 95)
    p10 = np.percentile(rms_frames, 10)
    return round(20 * np.log10((p95 + 1e-12) / (p10 + 1e-12)), 1)


# ── Public API ────────────────────────────────────────────────────────────────

def analyze_audio(input_path: Path) -> dict:
    """
    Analyze audio: BPM, key, loudness, spectral stats.
    Uses librosa when available.
    """
    t0       = time.perf_counter()
    data, sr = sf.read(str(input_path), always_2d=False)
    mono     = data.mean(axis=1) if data.ndim > 1 else data
    duration = round(len(data) / sr, 2)

    # ── Loudness
    rms          = float(np.sqrt(np.mean(mono ** 2)) + 1e-12)
    lufs_approx  = round(20 * np.log10(rms) - 0.7, 1)
    peak_db      = round(20 * np.log10(float(np.max(np.abs(mono))) + 1e-12), 1)
    dynamic_range = _dynamic_range(mono, sr)

    # ── Spectral centroid (perceptual brightness)
    n_fft = min(2048, len(mono))
    mag   = np.abs(np.fft.rfft(mono[:n_fft]))
    freqs = np.fft.rfftfreq(n_fft, 1 / sr)
    spectral_centroid = round(float(np.sum(freqs * mag) / (np.sum(mag) + 1e-9)), 0)

    # ── BPM + Key
    if _LIBROSA:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            y    = mono.astype(np.float32)
            sr_t = sr
            if sr > 22050:
                y    = librosa.resample(y, orig_sr=sr, target_sr=22050)
                sr_t = 22050
            tempo, _  = librosa.beat.beat_track(y=y, sr=sr_t)
            bpm       = round(float(np.atleast_1d(tempo)[0]), 1)
            chroma    = librosa.feature.chroma_cqt(y=y, sr=sr_t)
            cm        = chroma.mean(axis=1)
            root_idx  = int(np.argmax(cm))
            maj = sum(cm[(root_idx + i) % 12] for i in [0, 4, 7])
            minn = sum(cm[(root_idx + i) % 12] for i in [0, 3, 7])
            mode     = "major" if maj >= minn else "minor"
            key_root = _NOTE_NAMES[root_idx]
    else:
        bpm      = _bpm_numpy(mono, sr)
        key_root, mode = _key_numpy(mono, sr)

    return {
        "duration":             duration,
        "samplerate":           sr,
        "channels":             1 if data.ndim == 1 else data.shape[1],
        "bpm":                  bpm,
        "key":                  f"{key_root} {mode}",
        "key_root":             key_root,
        "key_mode":             mode,
        "lufs_approx":          lufs_approx,
        "peak_db":              peak_db,
        "dynamic_range_db":     dynamic_range,
        "spectral_centroid_hz": spectral_centroid,
        "librosa_used":         _LIBROSA,
        "processing_time":      round(time.perf_counter() - t0, 3),
    }
