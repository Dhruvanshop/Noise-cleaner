"""
De-reverberation via STFT spectral subtraction.

Estimates the late reverberation from an exponentially-weighted past-frame
magnitude and subtracts it from the current frame. Pure numpy/scipy.
"""
from __future__ import annotations

import io
import time
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import stft, istft


def _dereverberate_channel(
    data: np.ndarray,
    sr: int,
    strength: float = 0.7,
    decay_ms: float = 80.0,
    n_fft: int = 2048,
    hop: int = 512,
) -> np.ndarray:
    """
    Single-channel de-reverberation.
    strength: 0.0 = no change, 1.0 = maximum de-reverb
    decay_ms: estimated RT20 room decay in milliseconds
    """
    _, _, Z = stft(data, sr, nperseg=n_fft, noverlap=n_fft - hop)
    mag   = np.abs(Z)
    phase = np.angle(Z)

    # Reverb decay factor
    decay_frames = max(1, int(decay_ms * sr / (hop * 1000)))
    alpha = float(np.exp(-6.9 / decay_frames))   # decays to -60 dB

    # Exponential moving average of past magnitudes → reverb estimate
    reverb_est = np.zeros_like(mag)
    for t in range(1, mag.shape[1]):
        reverb_est[:, t] = alpha * reverb_est[:, t - 1] + (1 - alpha) * mag[:, t - 1]

    # Weighted spectral subtraction with gain floor
    gain_floor = 0.05
    gain = np.maximum(
        (mag - strength * reverb_est) / (mag + 1e-10),
        gain_floor,
    )

    Z_clean = gain * mag * np.exp(1j * phase)
    _, output = istft(Z_clean, sr, nperseg=n_fft, noverlap=n_fft - hop)

    # Match original length
    n = len(data)
    if len(output) > n:
        output = output[:n]
    elif len(output) < n:
        output = np.pad(output, (0, n - len(output)))

    return output.astype(data.dtype)


def dereverberate_audio(
    input_path: Path,
    output_dir: Path,
    *,
    strength: float = 0.7,
    decay_ms: float = 80.0,
    output_format: str = "wav",
) -> dict:
    """
    De-reverberate an audio file.
    Returns metadata dict with _out_path (internal, router pops it).
    """
    t0    = time.perf_counter()
    data, sr = sf.read(str(input_path), always_2d=False)

    if data.ndim == 1:
        result = _dereverberate_channel(data, sr, strength, decay_ms)
    else:
        channels = [
            _dereverberate_channel(data[:, i], sr, strength, decay_ms)
            for i in range(data.shape[1])
        ]
        result = np.column_stack(channels)

    # Prevent clipping
    peak = np.max(np.abs(result))
    if peak > 0.999:
        result = result / peak * 0.999

    task_id = uuid.uuid4().hex
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"dereverbed_{task_id[:8]}.{output_format}"
    _write(result, sr, out_path, output_format)

    return {
        "task_id":         task_id,
        "_out_path":       str(out_path),
        "output_format":   output_format,
        "duration":        round(len(data) / sr, 2),
        "samplerate":      sr,
        "channels":        1 if data.ndim == 1 else data.shape[1],
        "strength_used":   round(strength, 2),
        "processing_time": round(time.perf_counter() - t0, 2),
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
