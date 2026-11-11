"""Command-line interface for audio_loudness_normalizer."""

from __future__ import annotations

import argparse
import logging
import sys

from audio_loudness_normalizer.core import integrated_loudness, normalize, read_wav, write_wav
from audio_loudness_normalizer.errors import LoudnessError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())


def main(argv: list[str] | None = None) -> int:
    """Run the CLI.

    Args:
        argv: Optional list of command-line arguments. If None, sys.argv is used.

    Returns:
        Exit code: 0 success, 1 silent input, 2 usage/IO/unsupported error.
    """
    parser = argparse.ArgumentParser(
        prog="audio-loudness-normalizer",
        description="Measure and normalize loudness of PCM WAV files per BS.1770-4.",
    )
    parser.add_argument("input", help="Input WAV file")
    parser.add_argument("output", nargs="?", help="Output WAV file (if omitted, only measure)")
    parser.add_argument("--target", type=float, default=-23.0, help="Target LUFS (default: -23.0)")
    parser.add_argument(
        "--ceiling", type=float, default=-1.0, help="Peak ceiling in dBFS (default: -1.0)"
    )
    parser.add_argument("--measure", action="store_true", help="Only measure integrated loudness")

    args = parser.parse_args(argv)

    try:
        with open(args.input, "rb") as f:
            wav_data = f.read()
    except OSError as e:
        print(f"Error reading {args.input}: {e}", file=sys.stderr)
        return 2

    try:
        audio = read_wav(wav_data)
        measured = integrated_loudness(audio)
        if measured == float("-inf"):
            if len(audio.channels[0]) < round(0.4 * audio.rate):
                print("Input is too short (minimum 0.4 seconds)", file=sys.stderr)
            else:
                print("Input is silent or below gating threshold", file=sys.stderr)
            return 1

        if args.measure:
            print(f"integrated {measured:.1f} LUFS")
            return 0

        result = normalize(audio, target_lufs=args.target, peak_ceiling_dbfs=args.ceiling)
        print(f"measured {result.measured_lufs:.1f} LUFS, gain {result.gain_db:+.1f} dB")
        if args.output:
            try:
                out_bytes = write_wav(result.audio)
                with open(args.output, "wb") as f:
                    f.write(out_bytes)
            except OSError as e:
                print(f"Error writing {args.output}: {e}", file=sys.stderr)
                return 2
        return 0
    except LoudnessError as e:
        if e.code in ("silent", "too_short"):
            print(f"{e.code}: {e}".rstrip(), file=sys.stderr)
            return 1
        print(f"{e.code}: {e}".rstrip(), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
