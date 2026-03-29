"""
Audio format converter — WAV / FLAC / OGG / MP3 / M4A.
Uses soundfile for lossless formats, pydub+ffmpeg for MP3/M4A.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf


_SUPPORTED_FORMATS = ("wav", "flac", "ogg", "mp3", "m4a")


def convert_file(
    input_path:  str | Path,
    output_path: str | Path,
    output_format: str = "mp3",
    bitrate: int = 192,          # kbps — relevant for MP3/M4A
    sample_rate: int | None = None,  # None = keep original
) -> dict:
    """Convert audio to a different format / sample rate."""
    input_path  = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fmt = output_format.lower().lstrip(".")

    try:
        audio, sr = sf.read(str(input_path), always_2d=True)
        audio = audio.astype(np.float32)

        # Resample if requested
        if sample_rate and sample_rate != sr:
            import scipy.signal as sg
            n_out = int(len(audio) * sample_rate / sr)
            audio = sg.resample(audio, n_out).astype(np.float32)
            sr = sample_rate

        if fmt in ("wav", "flac", "ogg"):
            sf.write(str(output_path), audio, sr)
        elif fmt == "mp3":
            _to_mp3(audio, sr, output_path, bitrate)
        elif fmt in ("m4a", "aac"):
            _to_ffmpeg(audio, sr, output_path, "ipod")  # ipod = M4A container
        else:
            sf.write(str(output_path), audio, sr)

        return {
            "ok":       True,
            "format":   fmt,
            "samplerate": sr,
            "channels": audio.shape[1],
            "duration": round(len(audio) / sr, 2),
            "size":     output_path.stat().st_size,
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _to_mp3(audio: np.ndarray, sr: int, path: Path, bitrate: int) -> None:
    import io
    from pydub import AudioSegment
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    buf.seek(0)
    seg = AudioSegment.from_wav(buf)
    seg.export(str(path), format="mp3", bitrate=f"{bitrate}k")


def _to_ffmpeg(audio: np.ndarray, sr: int, path: Path, fmt: str) -> None:
    import io
    from pydub import AudioSegment
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    buf.seek(0)
    seg = AudioSegment.from_wav(buf)
    seg.export(str(path), format=fmt)
