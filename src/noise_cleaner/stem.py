"""
Vocal / stem separation using Facebook Research Demucs.

Supported models
----------------
htdemucs   (default) — 4 stems : drums · bass · other · vocals
htdemucs_6s          — 6 stems : drums · bass · other · vocals · guitar · piano

Both models are MIT-licensed.  The first run downloads the weights (~80 MB
each) to ~/.cache/torch/hub/.

Reference: https://github.com/facebookresearch/demucs
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf

# ── optional dependencies ──────────────────────────────────────────────────────
_DEMUCS_AVAILABLE = False
_DEMUCS_ERROR = ""

try:
    import torch
    import torchaudio
    from demucs.pretrained import get_model
    from demucs.apply import apply_model
    _DEMUCS_AVAILABLE = True
except ImportError as e:
    _DEMUCS_ERROR = str(e)


# ── model metadata ─────────────────────────────────────────────────────────────

#: Canonical stem names for each supported model.
MODEL_STEMS: Dict[str, List[str]] = {
    "htdemucs":   ["drums", "bass", "other", "vocals"],
    "htdemucs_6s": ["drums", "bass", "other", "vocals", "guitar", "piano"],
}

#: Convenience alias — default 4-stem list.
STEMS = MODEL_STEMS["htdemucs"]

#: Per-model cache so each model is loaded at most once per process.
_model_cache: Dict[str, object] = {}


def _get_model(name: str = "htdemucs"):
    """Load *name* from disk (or return cached instance)."""
    if name not in _model_cache:
        model = get_model(name)
        model.eval()
        _model_cache[name] = model
    return _model_cache[name]


# ── public API ─────────────────────────────────────────────────────────────────

def separate_file(
    input_path:      "str | Path",
    output_dir:      "str | Path",
    stems_requested: "Optional[List[str]]" = None,  # None = all stems for model
    output_format:   str = "wav",
    mp3_bitrate:     int = 192,
    model_name:      str = "htdemucs",
) -> dict:
    """
    Separate *input_path* into individual stems using Demucs.

    Parameters
    ----------
    input_path      : audio file to process
    output_dir      : directory where stem files are written
    stems_requested : list of stem names to keep (None = all available)
    output_format   : ``"wav"``, ``"mp3"``, ``"flac"``, or ``"ogg"``
    mp3_bitrate     : only used when *output_format* == ``"mp3"``
    model_name      : ``"htdemucs"`` (4 stems) or ``"htdemucs_6s"`` (6 stems)

    Returns
    -------
    ``{"ok": True, "stems": {name: path}, "duration": …, "samplerate": …, "channels": …}``
    or ``{"ok": False, "error": "…", "stems": {}}``
    """
    if not _DEMUCS_AVAILABLE:
        return {"ok": False, "error": _DEMUCS_ERROR, "stems": {}}

    import torch
    import torchaudio

    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    valid_stems = MODEL_STEMS.get(model_name, STEMS)
    if stems_requested is None:
        stems_requested = valid_stems
    else:
        # silently ignore unknown stems for the chosen model
        stems_requested = [s for s in stems_requested if s in valid_stems]
    if not stems_requested:
        return {"ok": False, "error": f"No valid stems requested for model '{model_name}'. "
                                      f"Available: {valid_stems}", "stems": {}}

    try:
        model = _get_model(model_name)
        model_sr: int = model.samplerate  # 44 100 Hz for both models

        # ── load audio ───────────────────────────────────────────────────────
        audio, sr = sf.read(str(input_path), always_2d=True)
        audio = audio.astype(np.float32)
        n_samples, n_ch = audio.shape

        wav = torch.from_numpy(audio.T)          # (C, T)

        # Demucs needs exactly 2 channels
        if wav.shape[0] == 1:
            wav = wav.repeat(2, 1)               # mono → stereo by duplication
        elif wav.shape[0] > 2:
            wav = wav[:2]                        # take first two channels

        # ── resample to model SR ─────────────────────────────────────────────
        if sr != model_sr:
            wav = torchaudio.functional.resample(wav, orig_freq=sr, new_freq=model_sr)

        # ── normalise amplitude ──────────────────────────────────────────────
        ref      = wav.mean(0)
        mean_ref = ref.mean()
        wav      = wav - mean_ref
        std_ref  = ref.std() + 1e-8
        wav      = wav / std_ref

        # ── run model ────────────────────────────────────────────────────────
        with torch.no_grad():
            sources = apply_model(
                model,
                wav.unsqueeze(0),
                device="cpu",
                shifts=0,
                split=True,
                overlap=0.25,
                progress=False,
            )[0]                                 # (stems, 2, T)

        # ── undo normalisation ───────────────────────────────────────────────
        sources = sources * std_ref + mean_ref

        # ── resample back ────────────────────────────────────────────────────
        if sr != model_sr:
            sources = torchaudio.functional.resample(
                sources, orig_freq=model_sr, new_freq=sr
            )

        stem_names         = model.sources       # ['drums','bass','other','vocals'(,'guitar','piano')]
        result_stems: dict = {}

        for i, stem_name in enumerate(stem_names):
            if stem_name not in stems_requested:
                continue

            stem_np = sources[i].T.numpy()       # (T, 2)
            if n_ch == 1:
                stem_np = stem_np.mean(axis=1, keepdims=True)

            ext      = output_format.lower()
            out_path = output_dir / f"{stem_name}.{ext}"
            _write_audio(stem_np, sr, out_path, ext, mp3_bitrate)
            result_stems[stem_name] = str(out_path)

        return {
            "ok":         True,
            "stems":      result_stems,
            "duration":   round(n_samples / sr, 2),
            "samplerate": sr,
            "channels":   n_ch,
        }

    except Exception as exc:
        return {"ok": False, "error": str(exc), "stems": {}}


# ── helpers ────────────────────────────────────────────────────────────────────

def _write_audio(
    audio:    np.ndarray,
    sr:       int,
    path:     Path,
    fmt:      str,
    bitrate:  int = 192,
) -> None:
    fmt = fmt.lower()
    if fmt in ("wav", "flac", "ogg"):
        sf.write(str(path), audio, sr)
    elif fmt == "mp3":
        import io
        from pydub import AudioSegment
        buf = io.BytesIO()
        sf.write(buf, audio, sr, format="WAV")
        buf.seek(0)
        AudioSegment.from_wav(buf).export(str(path), format="mp3", bitrate=f"{bitrate}k")
    else:
        sf.write(str(path), audio, sr)
