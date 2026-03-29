"""
caption.py — Subtitle utilities and caption burning for video files.

Features:
  - parse_srt / build_srt        — SRT text ↔ list-of-dicts
  - srt_to_vtt                   — SRT → WebVTT (for HTML5 <track> live preview)
  - get_available_fonts          — fc-list → subset of well-known fonts
  - burn_captions                — ffmpeg subtitles filter with full ASS style
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

_FFMPEG           = shutil.which("ffmpeg")
_FFMPEG_AVAILABLE = _FFMPEG is not None

# ── Font catalogue ────────────────────────────────────────────────

PRESET_FONTS = [
    "Arial", "Liberation Sans", "DejaVu Sans",
    "Roboto", "Open Sans", "Lato", "Montserrat", "Oswald",
    "Liberation Serif", "DejaVu Serif", "Times New Roman", "Georgia",
    "Courier New", "DejaVu Sans Mono", "Liberation Mono",
    "Impact", "Trebuchet MS",
]


def get_available_fonts() -> list[str]:
    """Return PRESET_FONTS that are installed on the system (via fc-list)."""
    try:
        r = subprocess.run(
            ["fc-list", "--format=%{family}\\n"],
            capture_output=True, text=True, timeout=5,
        )
        raw = r.stdout.lower()
        available = [f for f in PRESET_FONTS if f.lower() in raw]
        # Guarantee at least one usable font
        for fb in ("DejaVu Sans", "Liberation Sans"):
            if fb not in available:
                available.append(fb)
        return available or PRESET_FONTS[:4]
    except Exception:
        return ["Arial", "DejaVu Sans", "Liberation Sans"]


# ── SRT utilities ─────────────────────────────────────────────────

def parse_srt(srt_text: str) -> list[dict]:
    """Parse SRT text into ``[{index, start, end, text}, …]``."""
    entries: list[dict] = []
    for block in re.split(r"\n\s*\n", srt_text.strip()):
        lines = block.strip().splitlines()
        if len(lines) < 3:
            continue
        try:
            idx = int(lines[0].strip())
        except ValueError:
            continue
        m = re.match(
            r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
            lines[1].strip(),
        )
        if not m:
            continue
        entries.append({
            "index": idx,
            "start": m.group(1).replace(".", ","),
            "end":   m.group(2).replace(".", ","),
            "text":  "\n".join(lines[2:]),
        })
    return entries


def build_srt(entries: list[dict]) -> str:
    """Serialise a list of subtitle dicts back to SRT text."""
    parts = [
        f"{i}\n{e['start']} --> {e['end']}\n{e['text']}"
        for i, e in enumerate(entries, 1)
    ]
    return "\n\n".join(parts) + "\n"


def srt_to_vtt(srt_text: str) -> str:
    """Convert SRT text to WebVTT (comma timecodes → dots, add WEBVTT header)."""
    # Strip index lines because VTT doesn't require them (but they don't harm either)
    vtt = "WEBVTT\n\n"
    # Replace SRT comma in timecodes with VTT dot
    converted = re.sub(r"(\d{2}:\d{2}:\d{2}),(\d{3})", r"\1.\2", srt_text)
    vtt += converted
    return vtt


# ── ASS colour helper ─────────────────────────────────────────────

def _hex_to_bgr_ass(hex_color: str) -> str:
    """Convert ``#RRGGBB`` to ASS ``&H00BBGGRR&``."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = h[0]*2 + h[1]*2 + h[2]*2
    r, g, b = h[0:2], h[2:4], h[4:6]
    return f"&H00{b}{g}{r}&".upper()


# ── Caption burning ────────────────────────────────────────────────

def burn_captions(
    video_path: Path,
    srt_path:   Path,
    output_path: Path,
    *,
    font_name:     str  = "Arial",
    font_size:     int  = 24,
    primary_color: str  = "#FFFFFF",   # text colour
    outline_color: str  = "#000000",   # outline / shadow colour
    position:      str  = "bottom",    # "bottom" | "top"
    bold:          bool = False,
    italic:        bool = False,
    outline:       int  = 2,           # 0 = none … 3 = thick
    box:           bool = False,       # draw semi-transparent bg box
) -> dict:
    """
    Burn SRT captions into *video_path* → *output_path* using ffmpeg.

    Uses the ``subtitles`` filter with ``force_style`` for full ASS styling.
    Video stream is re-encoded (CPU/H.264) to bake in the subs; audio is copied.
    """
    if not _FFMPEG:
        return {"ok": False, "error": "ffmpeg not found — install ffmpeg"}

    try:
        pc  = _hex_to_bgr_ass(primary_color)
        oc  = _hex_to_bgr_ass(outline_color)
        aln = "2" if position == "bottom" else "6"  # ASS: 2=bot-centre 6=top-centre

        style_parts = [
            f"Fontname={font_name}",
            f"FontSize={font_size}",
            f"PrimaryColour={pc}",
            f"OutlineColour={oc}",
            f"Outline={outline}",
            f"Shadow=0",
            f"Bold={1 if bold else 0}",
            f"Italic={1 if italic else 0}",
            f"Alignment={aln}",
            "MarginV=20",
        ]
        if box:
            style_parts += ["BackColour=&H80000000&", "BorderStyle=4"]

        style = ",".join(style_parts)

        # ffmpeg path escaping for the subtitles filter
        srt_esc = (
            str(srt_path)
            .replace("\\", "/")
            .replace(":", "\\:")
            .replace("'", "\\'")
        )
        vf = f"subtitles='{srt_esc}':force_style='{style}'"

        r = subprocess.run(
            [_FFMPEG, "-y",
             "-i", str(video_path),
             "-vf", vf,
             "-c:v", "libx264", "-crf", "22", "-preset", "fast",
             "-c:a", "copy",
             str(output_path)],
            capture_output=True, text=True, timeout=3600,
        )
        if r.returncode != 0:
            return {"ok": False, "error": r.stderr[-1000:]}
        return {"ok": True}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "ffmpeg timed out"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
