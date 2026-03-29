from __future__ import annotations

import argparse
from pathlib import Path

from .denoise import DenoiseConfig, DenoiseResult, denoise_file


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="noise-clean",
        description="Remove noise from audio using asymmetric Wiener filtering.",
    )
    parser.add_argument("input",  type=Path, help="Input audio path (wav/flac/ogg)")
    parser.add_argument("output", type=Path, help="Output audio path")

    # Auto noise detection
    parser.add_argument("--use-vad",             action=argparse.BooleanOptionalAction, default=True,
                        help="Automatically detect noise vs speech (default: on)")
    parser.add_argument("--vad-aggressiveness",  type=int, choices=[0,1,2,3], default=2,
                        help="WebRTC VAD aggressiveness 0-3 (default: 2)")

    # Noise estimation
    parser.add_argument("--noise-frames-frac",      type=float, default=0.15)
    parser.add_argument("--n-std-thresh",            type=float, default=1.5)
    parser.add_argument("--noise-bias-correction",   type=float, default=1.25)

    # Wiener filter
    parser.add_argument("--prop-decrease",           type=float, default=0.90)
    parser.add_argument("--dd-alpha",                type=float, default=0.98)
    parser.add_argument("--gain-floor",              type=float, default=0.08)

    # Asymmetric gain smoothing
    parser.add_argument("--gain-smooth-attack",      type=float, default=0.40,
                        help="Attack alpha: fast suppression (default 0.40)")
    parser.add_argument("--gain-smooth-release",     type=float, default=0.92,
                        help="Release alpha: slow recovery, prevents voice modulation (default 0.92)")

    # Residual + passes
    parser.add_argument("--residual-sub-factor",     type=float, default=0.10)
    parser.add_argument("--n-passes",                type=int,   default=1)

    # STFT
    parser.add_argument("--n-fft",       type=int, default=2048)
    parser.add_argument("--hop-length",  type=int, default=512)
    parser.add_argument("--win-length",  type=int, default=2048)

    return parser


def main() -> None:
    args = build_parser().parse_args()

    cfg = DenoiseConfig(
        use_vad=args.use_vad,
        vad_aggressiveness=args.vad_aggressiveness,
        noise_frames_frac=args.noise_frames_frac,
        n_std_thresh=args.n_std_thresh,
        noise_bias_correction=args.noise_bias_correction,
        prop_decrease=args.prop_decrease,
        dd_alpha=args.dd_alpha,
        gain_floor=args.gain_floor,
        gain_smooth_attack=args.gain_smooth_attack,
        gain_smooth_release=args.gain_smooth_release,
        residual_sub_factor=args.residual_sub_factor,
        n_passes=args.n_passes,
        n_fft=args.n_fft,
        hop_length=args.hop_length,
        win_length=args.win_length,
    )

    result: DenoiseResult = denoise_file(args.input, args.output, cfg)
    engine_map = {"webrtcvad": "WebRTC VAD", "sfm": "Spectral VAD", "min_stats": "Min-Stats"}
    print(f"Saved denoised audio to: {result.output_path}")
    print(f"VAD engine : {engine_map.get(result.vad_engine, result.vad_engine)}")
    print(f"Speech     : {result.speech_fraction * 100:.1f} %  |  Noise: {(1 - result.speech_fraction) * 100:.1f} %")


def serve_ui() -> None:
    """Launch the drag-and-drop web UI."""
    import argparse
    from .server import serve

    parser = argparse.ArgumentParser(
        prog="noise-clean-ui",
        description="Start the Noise Cleaner web UI.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    parser.add_argument("--no-browser", action="store_true", help="Do not open browser automatically")
    args = parser.parse_args()
    serve(host=args.host, port=args.port, open_browser=not args.no_browser)


if __name__ == "__main__":
    main()
