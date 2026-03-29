"""
Local speech transcription using OpenAI Whisper.

Model: whisper (open-source, MIT license)
  • Runs 100% locally — no API key, no internet, no cost
  • Supports 75+ languages with auto-detection
  • Models: tiny (39M), base (74M), small (244M), medium (769M)
  • Default: base — good accuracy, fast (real-time on CPU)
  • Reference: https://github.com/openai/whisper
"""
from __future__ import annotations

import json
import time
from pathlib import Path

_WHISPER_AVAILABLE = False
_WHISPER_ERROR = ""

try:
    import whisper as _whisper_module
    _WHISPER_AVAILABLE = True
except ImportError as e:
    _WHISPER_ERROR = str(e)


_model_cache: dict[str, object] = {}    # size → model


def _get_model(model_size: str = "base"):
    if model_size not in _model_cache:
        import whisper as _w
        _model_cache[model_size] = _w.load_model(model_size)
    return _model_cache[model_size]


def transcribe_file(
    input_path: str | Path,
    output_dir:  str | Path | None = None,
    model_size:  str = "base",      # tiny | base | small | medium | large
    language:    str | None = None,  # None = auto-detect
    task:        str = "transcribe", # "transcribe" or "translate" (→ English)
) -> dict:
    """
    Transcribe an audio file using OpenAI Whisper.

    Returns:
      {
        ok, text, language, duration, segments: [{start, end, text}],
        srt_path (if output_dir given), txt_path (if output_dir given)
      }
    """
    if not _WHISPER_AVAILABLE:
        return {"ok": False, "error": _WHISPER_ERROR, "text": ""}

    input_path = Path(input_path)
    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        model = _get_model(model_size)

        opts: dict = {"task": task, "fp16": False}
        if language:
            opts["language"] = language

        result = model.transcribe(str(input_path), **opts)

        text:     str   = result.get("text", "").strip()
        lang:     str   = result.get("language", "")
        segments: list  = result.get("segments", [])

        # Compact segment format
        clean_segs = [
            {
                "start": round(float(s["start"]), 2),
                "end":   round(float(s["end"]),   2),
                "text":  s["text"].strip(),
            }
            for s in segments
        ]

        out: dict = {
            "ok":       True,
            "text":     text,
            "language": lang,
            "segments": clean_segs,
        }

        if output_dir:
            # Save plain text
            txt_path = output_dir / "transcript.txt"
            txt_path.write_text(text, encoding="utf-8")
            out["txt_path"] = str(txt_path)

            # Save SRT subtitle file
            srt_path = output_dir / "transcript.srt"
            srt_path.write_text(_to_srt(clean_segs), encoding="utf-8")
            out["srt_path"] = str(srt_path)

            # Save JSON
            json_path = output_dir / "transcript.json"
            json_path.write_text(
                json.dumps({"text": text, "language": lang, "segments": clean_segs},
                           ensure_ascii=False, indent=2),
                encoding="utf-8"
            )
            out["json_path"] = str(json_path)

        return out

    except Exception as exc:
        return {"ok": False, "error": str(exc), "text": ""}


def _to_srt(segments: list[dict]) -> str:
    """Convert Whisper segments to SRT subtitle format."""
    lines = []
    for i, seg in enumerate(segments, 1):
        start = _fmt_srt_time(seg["start"])
        end   = _fmt_srt_time(seg["end"])
        lines.append(f"{i}\n{start} --> {end}\n{seg['text']}\n")
    return "\n".join(lines)


def _fmt_srt_time(seconds: float) -> str:
    h  = int(seconds // 3600)
    m  = int((seconds % 3600) // 60)
    s  = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
