"""
Silence / dead-air remover.

Detects silent regions by RMS energy, removes (or compresses) them,
and writes the result as a WAV file.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


def trim_silence(
    input_path:      str | Path,
    output_path:     str | Path,
    min_silence_ms:  int   = 500,   # minimum run of silence to remove
    threshold_db:    float = -40.0, # below this = silence
    keep_padding_ms: int   = 80,    # leave this much silence on each edge of a cut
    output_format:   str   = "wav",
) -> dict:
    """
    Remove silence gaps longer than min_silence_ms from audio.

    Returns a metadata dict with durations and silence stats.
    """
    input_path  = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio, sr = sf.read(str(input_path), always_2d=True)
    audio = audio.astype(np.float32)
    n_samples, n_ch = audio.shape

    # ── Build per-sample silence mask using a sliding RMS window ──────
    frame_ms  = 20      # 20 ms analysis frames
    frame_n   = max(1, int(sr * frame_ms / 1000))
    hop_n     = frame_n // 2

    threshold_lin = 10 ** (threshold_db / 20.0)

    # Mono mix for detection
    mono = audio.mean(axis=1)
    n_frames = max(1, (n_samples - frame_n) // hop_n + 1)

    frame_rms = np.zeros(n_frames, dtype=np.float32)
    for i in range(n_frames):
        s = i * hop_n
        frame_rms[i] = float(np.sqrt(np.mean(mono[s : s + frame_n] ** 2)))

    # Per-frame silence flag
    is_silent = frame_rms < threshold_lin

    # Map frame silence flags back to sample-level
    sample_silent = np.zeros(n_samples, dtype=bool)
    for i in range(n_frames):
        s = i * hop_n
        e = min(s + frame_n, n_samples)
        if is_silent[i]:
            sample_silent[s:e] = True

    # ── Find silence runs and collect audio to keep ────────────────────
    min_n    = int(sr * min_silence_ms  / 1000)
    pad_n    = int(sr * keep_padding_ms / 1000)

    keep_mask = np.ones(n_samples, dtype=bool)  # start: keep everything

    i = 0
    removed_samples = 0
    silence_runs    = 0
    while i < n_samples:
        if sample_silent[i]:
            # Find end of this silence run
            j = i
            while j < n_samples and sample_silent[j]:
                j += 1
            run_len = j - i
            if run_len >= min_n:
                # Remove all but pad_n on each side
                cut_start = min(i + pad_n, j)
                cut_end   = max(j - pad_n, cut_start)
                keep_mask[cut_start:cut_end] = False
                removed_samples += cut_end - cut_start
                silence_runs += 1
            i = j
        else:
            i += 1

    out_audio = audio[keep_mask, :]

    # Write output
    _write_audio(out_audio, sr, output_path, output_format)

    orig_dur = n_samples / sr
    out_dur  = len(out_audio) / sr
    return {
        "ok":               True,
        "duration_in":      round(orig_dur, 2),
        "duration_out":     round(out_dur, 2),
        "removed_seconds":  round(removed_samples / sr, 2),
        "silence_runs":     silence_runs,
        "pct_removed":      round(removed_samples / max(n_samples, 1) * 100, 1),
    }


def _write_audio(audio: np.ndarray, sr: int, path: Path, fmt: str) -> None:
    fmt = fmt.lower()
    if fmt in ("wav", "flac", "ogg"):
        sf.write(str(path), audio, sr)
    elif fmt == "mp3":
        import io
        from pydub import AudioSegment
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        buf.seek(0)
        seg = AudioSegment.from_wav(buf)
        seg.export(str(path), format="mp3", bitrate="192k")
    else:
        sf.write(str(path), audio, sr)
