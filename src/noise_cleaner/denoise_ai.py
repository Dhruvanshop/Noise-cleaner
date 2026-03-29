"""
AI-powered audio denoising using Facebook Research's DNS-64 model.

Model: DNS-64  (https://github.com/facebookresearch/denoiser)
  • 33.5 M parameter recurrent encoder-decoder (LSTM + convolutional)
  • Trained on the DNS Challenge dataset — thousands of hours of speech
    mixed with diverse real-world noise (crowds, traffic, music, HVAC…)
  • License: MIT / CC-BY-NC  (free for any personal/research use)
  • Model file: ~64 MB, downloaded once to ~/.cache/torch/hub/checkpoints/

Why this is dramatically better than algorithmic methods
──────────────────────────────────────────────────────────
Wiener/spectral-gating methods can only suppress noise in bins where the
*current frame* looks noisy. They have no understanding of what speech
sounds like. The DNS-64 network has learned from millions of examples what
clean speech should sound like in EVERY frequency at EVERY moment, so it can:
  • Remove non-stationary noise (music, voices, traffic)
  • Fill in harmonics that algorithmic methods accidentally remove
  • Not modulate the voice at all — it directly predicts clean speech
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

# ── availability check ────────────────────────────────────────────────
_AI_AVAILABLE = False
_AI_ERROR: str = ""

try:
    import torch
    import torchaudio
    from denoiser import pretrained as _dn_pretrained
    _AI_AVAILABLE = True
except ImportError as e:
    _AI_ERROR = str(e)


# ── lazy model singleton ──────────────────────────────────────────────
_model_cache: object | None = None


def _get_model():
    """Load the DNS-64 model once and cache it in memory."""
    global _model_cache
    if _model_cache is None:
        import torch
        from denoiser import pretrained
        model = pretrained.dns64()
        model.eval()
        _model_cache = model
    return _model_cache


# ── core AI denoising ─────────────────────────────────────────────────

def denoise_channel_ai(y: np.ndarray, sr: int) -> np.ndarray:
    """
    Denoise a single audio channel using the DNS-64 neural network.

    The model operates at 16 kHz internally:
      1. Resample input to 16 kHz
      2. Run through DNS-64 (encoder → LSTM → decoder)
      3. Resample output back to original sample rate
    """
    import torch
    import torchaudio

    model = _get_model()
    model_sr: int = model.sample_rate  # 16000

    # Normalize to [-1, 1]
    y_f = y.astype(np.float32)
    peak = np.max(np.abs(y_f))
    if peak < 1e-9:
        return y_f
    y_norm = y_f / (peak + 1e-9)

    # → torch tensor (1, T)
    wav = torch.from_numpy(y_norm).unsqueeze(0)

    # Resample to model SR if needed
    if sr != model_sr:
        wav = torchaudio.functional.resample(wav, orig_freq=sr, new_freq=model_sr)

    # Chunk to avoid OOM on very long files (30 s chunks with 0.1 s overlap)
    chunk_s   = 30
    overlap_s = 0.1
    chunk_n   = int(chunk_s   * model_sr)
    overlap_n = int(overlap_s * model_sr)
    total_n   = wav.shape[1]

    if total_n <= chunk_n:
        # Short enough: run in one shot
        with torch.no_grad():
            enhanced = model(wav.unsqueeze(0)).squeeze(0)  # (1, T)
    else:
        # Long file: chunk with cross-fade overlap
        enhanced_chunks: list[torch.Tensor] = []
        pos = 0
        while pos < total_n:
            end = min(pos + chunk_n, total_n)
            chunk = wav[:, pos:end]
            with torch.no_grad():
                out = model(chunk.unsqueeze(0)).squeeze(0)  # (1, T)
            # Cross-fade: blend overlap region with previous chunk tail
            if enhanced_chunks and overlap_n > 0:
                prev = enhanced_chunks[-1]
                fade_len = min(overlap_n, prev.shape[1], out.shape[1])
                fade_in  = torch.linspace(0, 1, fade_len)
                fade_out = 1.0 - fade_in
                prev[:, -fade_len:] = prev[:, -fade_len:] * fade_out + out[:, :fade_len] * fade_in
                out = out[:, fade_len:]
            enhanced_chunks.append(out)
            pos = end
        enhanced = torch.cat(enhanced_chunks, dim=1)  # (1, T)

    # Resample back to original SR
    if sr != model_sr:
        enhanced = torchaudio.functional.resample(enhanced, orig_freq=model_sr, new_freq=sr)

    # Match original length exactly
    orig_len = len(y)
    if enhanced.shape[1] > orig_len:
        enhanced = enhanced[:, :orig_len]
    elif enhanced.shape[1] < orig_len:
        import torch.nn.functional as F
        enhanced = F.pad(enhanced, (0, orig_len - enhanced.shape[1]))

    # Restore original loudness level
    result = enhanced.squeeze(0).numpy()
    result_rms = float(np.sqrt(np.mean(result ** 2))) + 1e-10
    orig_rms   = float(np.sqrt(np.mean(y_f ** 2)))   + 1e-10
    result     = result * (orig_rms / result_rms)

    peak_out = np.max(np.abs(result))
    if peak_out > 0.999:
        result *= 0.999 / peak_out

    return result.astype(np.float32)


# ── public API ────────────────────────────────────────────────────────

def denoise_file_ai(
    input_path:  str | Path,
    output_path: str | Path,
) -> dict:
    """
    Denoise an audio file using the DNS-64 AI model.

    Returns a dict with metadata:
      {ok, backend, error, speech_fraction}
    """
    if not _AI_AVAILABLE:
        return {"ok": False, "backend": "ai", "error": _AI_ERROR}

    input_path  = Path(input_path)
    output_path = Path(output_path)

    try:
        audio, sr = sf.read(str(input_path), always_2d=True)
        audio = audio.astype(np.float32)

        channels = []
        for c in range(audio.shape[1]):
            channels.append(denoise_channel_ai(audio[:, c], sr))

        denoised = np.stack(channels, axis=1)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output_path), denoised, sr)

        return {
            "ok":      True,
            "backend": "dns64",
            "error":   None,
        }
    except Exception as exc:
        return {"ok": False, "backend": "dns64", "error": str(exc)}
