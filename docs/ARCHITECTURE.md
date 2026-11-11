# Architecture

This document describes the design of the `audio_loudness_normalizer` package.

## Overview

The package implements ITU-R BS.1770-4 loudness measurement and normalization for PCM WAV audio in pure Python. It uses only the standard library, making it lightweight and portable.

## Components

### Core Module (`core.py`)

- **Audio**: Frozen dataclass holding sample rate and channels (tuples of floats in `[-1.0, 1.0]`). It accepts 1 or 2 channels, requires all channels to have the same non-zero length, and rejects other shapes.
- **NormalizeResult**: Frozen dataclass containing normalized audio, measured loudness, applied gain, and the `peak_limited` flag.
- **read_wav / write_wav**: Parse and produce WAV bytes, handling uncompressed PCM 16-bit only. `read_wav` divides int16 samples by 32768.0; `write_wav` uses `round(x * 32767)` half-to-even rounding, clips to the int16 range, and does not dither.
- **k_weighting**: Returns two biquad filters (high shelf and high-pass) per BS.1770-4. For 48000 Hz it uses the exact table coefficients; for other rates from 8000 to 192000 Hz it uses the bilinear-transform derivation.
- **integrated_loudness**: Applies K-weighting, computes block energies with 0.4 s blocks starting every 0.1 s, applies the -70 LUFS absolute gate and the relative gate 10 LU below the mean of the absolute-gated blocks, and returns integrated LUFS or `float('-inf')` when no block passes.
- **normalize**: Applies gain to reach the target loudness, reducing gain when needed so the sample peak does not exceed the ceiling. It returns the applied gain and whether the peak ceiling limited the result.

### Error Handling

`LoudnessError` provides a machine-readable `code` attribute with the literal values `too_short`, `unsupported_format`, `input_too_long`, `silent`, `invalid_wav`, and `invalid_target`. Error messages are truncated to at most 200 characters.

### CLI (`__main__.py`)

Provides a command-line interface for measuring and normalizing WAV files. Options are `--target` (default -23.0), `--ceiling` (default -1.0), and `--measure`. Exit codes: 0 success, 1 silent or too-short input, 2 usage, I/O, or unsupported-format error.

## Design Decisions

- **No external dependencies**: The algorithm is implemented with pure Python loops and standard library modules, ensuring portability and auditability.
- **Strict validation**: Audio objects are immutable and enforce channel count and equal channel lengths.
- **Logging**: Uses `logging.getLogger(__name__)` with a `NullHandler` to avoid interfering with applications.

## Testing

The supplied tests are `tests/test_audio_loudness_normalizer.py` and `tests/test_cli.py`. They use pytest, generate WAV data in temporary directories, and assert public exports, measurement and normalization behavior, CLI output and exit codes, and error codes.
