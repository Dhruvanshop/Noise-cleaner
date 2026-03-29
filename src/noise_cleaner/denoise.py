"""
Audio denoising with automatic noise/speech detection.

Noise-detection pipeline (auto, in priority order)
───────────────────────────────────────────────────
1. WebRTC VAD  (if `webrtcvad` package present)
   • Battle-tested speech detector used in Google Chrome / WebRTC.
   • Runs at 16 kHz; the audio is resampled for VAD only — denoising
     still happens at the original sample rate.
   • Aggressiveness 0–3: 0 = very lenient, 3 = very strict.

2. Spectral Flatness Measure (SFM) + Energy VAD  (pure numpy fallback)
   • Spectral Flatness = geometric_mean(|X|²) / arithmetic_mean(|X|²)
     → 1.0 for white noise (flat spectrum)
     → ~0.0 for voiced speech (harmonic peaks)
   • Combined with adaptive log-energy threshold for silence detection.
   • Requires zero extra packages.

3. Minimum-statistics  (last resort)
   • Uses the M% quietest frames by energy as the noise profile.

Denoising pipeline
──────────────────
• Hann-windowed STFT, 75 % overlap, perfect OLA reconstruction.
• Per-bin noise power from VAD-selected noise frames.
• Decision-directed Wiener soft gain.
• Asymmetric attack/release gain smoothing (prevents voice modulation).
• Mild residual power-domain spectral subtraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import gcd
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf
from scipy.ndimage import gaussian_filter1d
from scipy.signal import get_window, resample_poly

# Optional: WebRTC VAD
_WEBRTCVAD_AVAILABLE = False
try:
    import webrtcvad as _wrtcvad_mod
    _WEBRTCVAD_AVAILABLE = True
except ImportError:
    pass


# ─────────────────────────────────────────────────── config ──────────

@dataclass(slots=True)
class DenoiseConfig:
    # ── Automatic noise detection ─────────────────────────────────────
    use_vad: bool = True
    """Enable automatic speech/noise detection.
    Uses WebRTC VAD if installed, else Spectral Flatness VAD."""

    vad_aggressiveness: int = 2
    """WebRTC VAD aggressiveness 0–3 (0=lenient, 3=very strict).
    Only applies when webrtcvad package is available."""

    # ── Noise estimation fallback ─────────────────────────────────────
    noise_frames_frac: float = 0.15
    """Fraction of quietest frames used when VAD falls back to min-stats."""

    n_std_thresh: float = 1.5
    """Noise threshold multiplier (σ). Higher = less noise removed."""

    noise_bias_correction: float = 1.25
    """Bias correction — min-stats underestimates true noise power."""

    noise_freq_smooth_sigma: float = 2.0
    """Gaussian frequency-axis smoothing of noise estimate (in bins)."""

    # ── Wiener filter ─────────────────────────────────────────────────
    dd_alpha: float = 0.98
    """Decision-directed prior-SNR smoothing coefficient."""

    gain_floor: float = 0.08
    """Minimum gain floor — prevents spectral holes and musical noise."""

    prop_decrease: float = 0.90
    """Maximum suppression strength [0–1]."""

    # ── Asymmetric gain smoothing ─────────────────────────────────────
    gain_smooth_attack: float = 0.40
    """IIR alpha when gain FALLS (noise detected) — fast suppression."""

    gain_smooth_release: float = 0.92
    """IIR alpha when gain RISES (speech returns) — slow recovery.
    Prevents the Wiener gain from tracking syllabic speech amplitude,
    which is the root cause of voice modulation artifacts."""

    # ── Residual subtraction ──────────────────────────────────────────
    residual_sub_factor: float = 0.10

    # ── STFT ──────────────────────────────────────────────────────────
    n_fft: int = 2048
    hop_length: int = 512
    win_length: int = 2048

    # ── Passes ────────────────────────────────────────────────────────
    n_passes: int = 1


@dataclass(slots=True)
class DenoiseResult:
    """Metadata returned by denoise_file()."""
    output_path: Path
    vad_used: bool = False
    vad_engine: str = "min_stats"   # "webrtcvad" | "sfm" | "min_stats"
    speech_fraction: float = 0.0   # fraction of frames identified as speech


# ─────────────────────────────────────────────────── STFT utils ──────

def _hann_stft(y: np.ndarray, cfg: DenoiseConfig) -> np.ndarray:
    win = get_window("hann", cfg.win_length, fftbins=True)
    pad = cfg.hop_length - (len(y) % cfg.hop_length)
    y_pad = np.pad(y, (cfg.win_length // 2, cfg.win_length // 2 + pad))
    n_frames = 1 + (len(y_pad) - cfg.win_length) // cfg.hop_length
    n_bins = cfg.n_fft // 2 + 1
    out = np.zeros((n_bins, n_frames), dtype=np.complex64)
    for t in range(n_frames):
        s = t * cfg.hop_length
        out[:, t] = np.fft.rfft(y_pad[s: s + cfg.win_length] * win, n=cfg.n_fft)
    return out


def _hann_istft(stft_mat: np.ndarray, cfg: DenoiseConfig, orig_len: int) -> np.ndarray:
    win = get_window("hann", cfg.win_length, fftbins=True)
    n_frames = stft_mat.shape[1]
    out_len = cfg.win_length // 2 + n_frames * cfg.hop_length + cfg.win_length // 2
    out  = np.zeros(out_len, dtype=np.float64)
    norm = np.zeros(out_len, dtype=np.float64)
    for t in range(n_frames):
        frame = np.fft.irfft(stft_mat[:, t], n=cfg.n_fft)[: cfg.win_length]
        s = t * cfg.hop_length
        out [s: s + cfg.win_length] += frame * win
        norm[s: s + cfg.win_length] += win ** 2
    norm = np.where(norm < 1e-8, 1.0, norm)
    trim = cfg.win_length // 2
    return (out / norm)[trim: trim + orig_len].astype(np.float32)


# ─────────────────────────────────────────────── automatic VAD ───────

def _webrtcvad_noise_mask(
    y: np.ndarray,
    sr: int,
    n_stft_frames: int,
    hop_length: int,
    aggressiveness: int,
) -> np.ndarray | None:
    """
    WebRTC VAD: classify audio as speech / non-speech at 30 ms frames.
    Returns boolean noise mask aligned to STFT frames, or None on failure.
    """
    if not _WEBRTCVAD_AVAILABLE:
        return None
    try:
        VAD_SR    = 16000
        FRAME_MS  = 30
        g         = gcd(int(sr), VAD_SR)
        y_16k     = resample_poly(y.astype(np.float64), VAD_SR // g, int(sr) // g)
        y_16k     = np.clip(y_16k, -1.0, 1.0)
        y_int16   = (y_16k * 32767).astype(np.int16)

        vad_obj         = _wrtcvad_mod.Vad(int(aggressiveness))
        vad_frame_len   = int(VAD_SR * FRAME_MS / 1000)          # 480 samples
        n_vad_frames    = len(y_int16) // vad_frame_len
        if n_vad_frames == 0:
            return None

        vad_speech = np.zeros(n_vad_frames, dtype=bool)
        for i in range(n_vad_frames):
            fb = y_int16[i * vad_frame_len: (i + 1) * vad_frame_len].tobytes()
            try:
                vad_speech[i] = vad_obj.is_speech(fb, VAD_SR)
            except Exception:
                vad_speech[i] = True          # assume speech on error

        # Map STFT frames to VAD frames via centre-sample timestamp
        vad_dur_s    = FRAME_MS / 1000.0
        noise_mask   = np.zeros(n_stft_frames, dtype=bool)
        for t in range(n_stft_frames):
            vi = int((t * hop_length / sr) / vad_dur_s)
            if vi < n_vad_frames:
                noise_mask[t] = not vad_speech[vi]

        if noise_mask.sum() < 4:
            return None
        return noise_mask
    except Exception:
        return None


def _sfm_noise_mask(power: np.ndarray) -> np.ndarray:
    """
    Spectral Flatness Measure + energy VAD (pure numpy, no extra deps).

    Spectral flatness = exp(mean(log P)) / mean(P)
      → near 1.0  :  flat / noise-like spectrum
      → near 0.0  :  tonal / harmonic spectrum (speech, music)

    Frames with high SFM OR very low energy are classified as noise.
    An adaptive energy threshold separates speech silences from noise.
    """
    eps = 1e-12
    # Per-frame SFM
    log_geo = np.mean(np.log(power + eps), axis=0)
    arith   = np.mean(power, axis=0) + eps
    sfm     = np.exp(log_geo) / arith                # (n_frames,)

    # Per-frame log energy
    log_e = 10.0 * np.log10(np.mean(power, axis=0) + eps)

    # Adaptive energy threshold: find the largest gap in the lower half
    # of the sorted energy distribution (natural noise-floor boundary)
    sorted_e = np.sort(log_e)
    lower    = sorted_e[: max(2, len(sorted_e) // 2)]
    gaps     = np.diff(lower)
    if len(gaps) > 0:
        gi      = int(np.argmax(gaps))
        e_thr   = float((lower[gi] + lower[gi + 1]) / 2.0)
    else:
        e_thr   = float(np.percentile(log_e, 30))

    # SFM threshold: top-35 % flattest frames are likely noise
    sfm_thr    = float(np.percentile(sfm, 65))
    noise_mask = (sfm > sfm_thr) | (log_e < e_thr)

    # Safety clamp: noise fraction must be in [5 %, 70 %]
    n, nf = len(noise_mask), int(noise_mask.sum())
    if nf < max(4, int(0.05 * n)):
        noise_mask = log_e < np.percentile(log_e, 15)
    elif nf > int(0.70 * n):
        noise_mask = log_e < np.percentile(log_e, 25)

    return noise_mask


def _min_stats_noise_mask(power: np.ndarray, frac: float) -> np.ndarray:
    """Fallback: select the M% quietest frames as noise."""
    n = power.shape[1]
    m = max(4, int(n * frac))
    idx  = np.argsort(power.mean(axis=0))[:m]
    mask = np.zeros(n, dtype=bool)
    mask[idx] = True
    return mask


# ─────────────────────────────────────────────── noise estimation ─────

def _estimate_noise_power(
    power:      np.ndarray,
    cfg:        DenoiseConfig,
    noise_mask: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Estimate per-bin noise power statistics from the selected noise frames.
    Uses median (robust to outliers) + bias correction + frequency smoothing.
    """
    nf = power[:, noise_mask]
    noise_med = np.median(nf, axis=1)
    noise_var = nf.var(axis=1) + 1e-12
    noise_med *= cfg.noise_bias_correction
    noise_med  = gaussian_filter1d(noise_med, sigma=cfg.noise_freq_smooth_sigma)
    return noise_med[:, np.newaxis], noise_var[:, np.newaxis]


# ─────────────────────────────────────────────────── gain smoothing ──

def _asymmetric_smooth(
    wiener: np.ndarray,
    alpha_attack: float,
    alpha_release: float,
) -> np.ndarray:
    """
    Asymmetric causal IIR smoothing.
      • Gain falling → use alpha_attack  (fast: suppress noise quickly)
      • Gain rising  → use alpha_release (slow: do NOT track speech envelope)
    This decouples the gain from syllabic speech amplitude — the primary
    fix for voice modulation artifacts.
    """
    s = np.empty_like(wiener)
    s[:, 0] = wiener[:, 0]
    for t in range(1, wiener.shape[1]):
        prev  = s[:, t - 1]
        curr  = wiener[:, t]
        alpha = np.where(curr >= prev, alpha_release, alpha_attack)
        s[:, t] = alpha * prev + (1.0 - alpha) * curr
    return s


# ─────────────────────────────────────────────────── core algorithm ──

def _denoise_pass(
    y:         np.ndarray,
    cfg:       DenoiseConfig,
    noise_mu:  np.ndarray,
    noise_var: np.ndarray,
) -> np.ndarray:
    stft_mat    = _hann_stft(y, cfg)
    power       = np.abs(stft_mat) ** 2
    n_frames    = power.shape[1]
    eps         = 1e-12

    # Decision-directed Wiener gain
    snr_post    = np.maximum(power / (noise_mu + eps) - 1.0, 0.0)
    snr_prior   = np.empty_like(power)
    snr_prior[:, 0] = snr_post[:, 0]
    for t in range(1, n_frames):
        snr_prior[:, t] = (
            cfg.dd_alpha * snr_prior[:, t - 1]
            + (1.0 - cfg.dd_alpha) * snr_post[:, t]
        )

    wiener = snr_prior / (1.0 + snr_prior)
    wiener = cfg.gain_floor + (np.clip(wiener, cfg.gain_floor, 1.0) - cfg.gain_floor) * cfg.prop_decrease
    wiener = _asymmetric_smooth(wiener, cfg.gain_smooth_attack, cfg.gain_smooth_release)

    mag   = np.abs(stft_mat)
    phase = stft_mat / (mag + eps)
    new_p = (mag * wiener) ** 2
    new_p = np.maximum(new_p - cfg.residual_sub_factor * noise_mu, (cfg.gain_floor * mag) ** 2)

    return _hann_istft(np.sqrt(new_p) * phase, cfg, len(y))


def _denoise_channel(
    y: np.ndarray,
    sr: int,
    cfg: DenoiseConfig,
) -> tuple[np.ndarray, bool, str, float]:
    """Returns (denoised, vad_used, vad_engine, speech_fraction)."""
    stft_raw  = _hann_stft(y, cfg)
    power_raw = np.abs(stft_raw) ** 2
    n_frames  = power_raw.shape[1]

    vad_used   = False
    vad_engine = "min_stats"
    noise_mask = None

    if cfg.use_vad:
        # 1) WebRTC VAD (most accurate)
        if _WEBRTCVAD_AVAILABLE:
            noise_mask = _webrtcvad_noise_mask(
                y, sr, n_frames, cfg.hop_length, cfg.vad_aggressiveness
            )
            if noise_mask is not None:
                vad_used, vad_engine = True, "webrtcvad"

        # 2) Spectral Flatness VAD (pure numpy fallback)
        if noise_mask is None:
            noise_mask = _sfm_noise_mask(power_raw)
            vad_used, vad_engine = True, "sfm"

    # 3) Minimum-statistics (last resort)
    if noise_mask is None:
        noise_mask = _min_stats_noise_mask(power_raw, cfg.noise_frames_frac)

    speech_fraction = float((~noise_mask).sum() / n_frames)
    noise_mu, noise_var = _estimate_noise_power(power_raw, cfg, noise_mask)

    # Noise profile estimated once from the ORIGINAL signal, reused across passes
    current = y.copy()
    for _ in range(max(1, cfg.n_passes)):
        current = _denoise_pass(current, cfg, noise_mu, noise_var)

    return current, vad_used, vad_engine, speech_fraction


# ─────────────────────────────────────────────────── public API ──────

def denoise_file(
    input_path:  str | Path,
    output_path: str | Path,
    config:      Optional[DenoiseConfig] = None,
) -> DenoiseResult:
    cfg          = config or DenoiseConfig()
    input_path   = Path(input_path)
    output_path  = Path(output_path)

    audio, sr = sf.read(str(input_path), always_2d=True)
    audio     = audio.astype(np.float32)

    result    = DenoiseResult(output_path=output_path)
    channels  = []

    for c in range(audio.shape[1]):
        ch_out, vad_used, vad_engine, speech_frac = _denoise_channel(
            audio[:, c], sr, cfg
        )
        channels.append(ch_out)
        if c == 0:
            result.vad_used        = vad_used
            result.vad_engine      = vad_engine
            result.speech_fraction = speech_frac

    denoised = np.stack(channels, axis=1)

    # Loudness match: preserve original RMS
    orig_rms = float(np.sqrt(np.mean(audio ** 2))) + 1e-10
    deno_rms = float(np.sqrt(np.mean(denoised ** 2))) + 1e-10
    denoised *= orig_rms / deno_rms
    peak = np.max(np.abs(denoised))
    if peak > 0.999:
        denoised *= 0.999 / peak

    output_path.parent.mkdir(parents=True, exist_ok=True)
    sf.write(str(output_path), denoised, sr)
    return result
