"""
Stem remixer — load stems from a completed job, apply per-stem volumes / mutes,
and export a mixed-down audio file.
"""
from __future__ import annotations

import time
import uuid
from pathlib import Path
from typing import Dict, Set

import numpy as np
import soundfile as sf


def remix_stems(
    stems_dir: Path,
    output_dir: Path,
    *,
    volumes: Dict[str, float] | None = None,
    muted: Set[str] | None = None,
    output_format: str = "wav",
    normalize: bool = True,
) -> dict:
    """
    Mix stems from *stems_dir* with optional per-stem volume scaling.

    Parameters
    ----------
    stems_dir     : directory that contains ``<stem>.wav`` files (job output)
    output_dir    : where the mixed file is written
    volumes       : mapping stem-name → linear gain (0 = silence, 1 = unity, 2 = +6 dB)
    muted         : set of stem names to silence completely
    output_format : "wav" | "flac" | "mp3" | "ogg" | "aac"
    normalize     : peak-normalise the mix to –1 dBFS before writing
    """
    t0       = time.perf_counter()
    volumes  = volumes or {}
    muted    = muted   or set()

    stem_files = sorted(stems_dir.glob("*.wav"))
    if not stem_files:
        raise FileNotFoundError(f"No WAV stems found in {stems_dir}")

    # ── Load all stems (resample to common rate + length) ────────────────────
    arrays: list[np.ndarray] = []
    sr_ref = None

    for sf_path in stem_files:
        stem_name = sf_path.stem.lower()
        if stem_name in muted:
            continue
        data, sr = sf.read(str(sf_path), always_2d=True)
        if sr_ref is None:
            sr_ref = sr
        elif sr != sr_ref:
            # Simple nearest-sample resample (librosa not required)
            ratio     = sr_ref / sr
            new_len   = int(len(data) * ratio)
            indices   = (np.arange(new_len) / ratio).astype(int).clip(0, len(data) - 1)
            data      = data[indices]

        vol = float(volumes.get(stem_name, 1.0))
        arrays.append(data * vol)

    if not arrays:
        raise ValueError("All stems are muted — nothing to mix.")

    # ── Align lengths ─────────────────────────────────────────────────────────
    max_len = max(a.shape[0] for a in arrays)
    max_ch  = max(a.shape[1] for a in arrays)

    def _pad(a: np.ndarray) -> np.ndarray:
        if a.shape[0] < max_len:
            a = np.pad(a, ((0, max_len - a.shape[0]), (0, 0)))
        if a.shape[1] < max_ch:
            a = np.tile(a, (1, max_ch // a.shape[1]))
        return a

    mix = sum(_pad(a) for a in arrays)   # type: ignore[assignment]
    mix = mix / (len(arrays) * 1.0)      # prevent gross clipping

    # ── Normalise ─────────────────────────────────────────────────────────────
    if normalize:
        peak = float(np.max(np.abs(mix)) + 1e-12)
        if peak > 0.891:                  # louder than –1 dBFS
            mix = mix * (0.891 / peak)

    # ── Write ─────────────────────────────────────────────────────────────────
    task_id    = uuid.uuid4().hex
    output_dir.mkdir(parents=True, exist_ok=True)
    _EXT_FORMAT = {"mp3": "mp3", "ogg": "ogg", "flac": "flac", "aac": "flac", "wav": "wav"}
    ext        = _EXT_FORMAT.get(output_format, "wav")
    out_path   = output_dir / f"remix_{task_id}.{ext}"

    sf_subtype = "PCM_16" if ext in ("wav", "flac") else None
    if sf_subtype:
        sf.write(str(out_path), mix if mix.shape[1] > 1 else mix[:, 0], sr_ref, subtype=sf_subtype)
    else:
        sf.write(str(out_path), mix if mix.shape[1] > 1 else mix[:, 0], sr_ref)

    return {
        "task_id":          task_id,
        "_out_path":        str(out_path),
        "stems_mixed":      [p.stem for p in stem_files if p.stem.lower() not in muted],
        "stems_muted":      list(muted),
        "duration":         round(max_len / sr_ref, 2),
        "samplerate":       sr_ref,
        "channels":         max_ch,
        "output_format":    output_format,
        "processing_time":  round(time.perf_counter() - t0, 3),
    }
