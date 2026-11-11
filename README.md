# trysac-audio-loudness-normalizer

[![Python Version](https://img.shields.io/pypi/pyversions/trysac-audio-loudness-normalizer.svg)](https://pypi.org/project/trysac-audio-loudness-normalizer/)
[![PyPI](https://img.shields.io/pypi/v/trysac-audio-loudness-normalizer.svg)](https://pypi.org/project/trysac-audio-loudness-normalizer/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Pure Python implementation of ITU-R BS.1770-4 integrated loudness measurement and normalization for PCM WAV audio. No runtime dependencies; the package uses only the standard library (`wave`, `math`, `array`, `io`, `logging`, `dataclasses`).

## Features

- Measure integrated loudness (LUFS) according to BS.1770-4 with K-weighting and gating.
- Normalize audio to a target loudness with a sample-peak ceiling.
- Read and write 16-bit PCM WAV files (mono/stereo, sample rates 8-192 kHz).
- Command-line interface for measurement and normalization.
- Strict error handling with machine-readable codes.

## Installation

```bash
pip install trysac-audio-loudness-normalizer
```

## Usage

### Python API

```python
from audio_loudness_normalizer import integrated_loudness, normalize, read_wav, write_wav

with open("input.wav", "rb") as f:
    audio = read_wav(f.read())
print(f"{integrated_loudness(audio):.1f} LUFS")
result = normalize(audio, target_lufs=-16.0, peak_ceiling_dbfs=-1.0)
with open("output.wav", "wb") as f:
    f.write(write_wav(result.audio))
```

### Command-line

```bash
# Measure loudness
audio-loudness-normalizer input.wav --measure

# Normalize to -16 LUFS and write output
audio-loudness-normalizer input.wav output.wav --target -16 --ceiling -1
```

## Public API

| Name | Behavior and limits |
|---|---|
| `Audio(rate: int, channels: tuple[tuple[float, ...], ...])` | Frozen dataclass. Supports 1 or 2 channels only; all channels must have the same non-zero length; samples are expected in the range `[-1.0, 1.0]`. |
| `read_wav(data: bytes, *, max_seconds: float = 600.0) -> Audio` | Parses uncompressed PCM 16-bit WAV, 1 or 2 channels, sample rate from 8000 to 192000 Hz. Converts int16 samples with `value / 32768.0`. Raises `LoudnessError` with codes `unsupported_format`, `input_too_long`, or `invalid_wav`. |
| `write_wav(audio: Audio) -> bytes` | Encodes PCM 16-bit uncompressed WAV. Converts samples with `round(x * 32767)` using half-to-even rounding, then clips to `[-32768, 32767]`; no dither is applied. Raises `LoudnessError` with code `unsupported_format` for channel counts or rates outside the supported range. |
| `k_weighting(rate: int) -> tuple[Biquad, Biquad]` | Returns the shelf and high-pass biquad filters. For 48000 Hz it returns the exact BS.1770-4 Annex 1 table coefficients; for other rates from 8000 to 192000 Hz it uses the bilinear-transform derivation. Raises `LoudnessError` with code `unsupported_format` outside that rate range. `Biquad` is `tuple[list[float], list[float]]`. |
| `integrated_loudness(audio: Audio) -> float` | Applies K-weighting, uses 0.4 s blocks starting every 0.1 s, an absolute gate at -70 LUFS, and a relative gate 10 LU below the mean of the absolute-gated blocks. Returns `float('-inf')` when no block passes the gates. |
| `normalize(audio: Audio, *, target_lufs: float = -23.0, peak_ceiling_dbfs: float = -1.0) -> NormalizeResult` | Requires `target_lufs` in `[-70, 0]` and `peak_ceiling_dbfs <= 0`. Audio shorter than 0.4 s raises `too_short`; silent or below-gate input raises `silent`. The ceiling is a sample peak ceiling, not true peak. Returns `NormalizeResult(audio, measured_lufs, gain_db, peak_limited)`. |
| `LoudnessError` | Exception carrying a machine-readable `code`: `too_short`, `unsupported_format`, `input_too_long`, `silent`, `invalid_wav`, or `invalid_target`. Messages are truncated to at most 200 characters. |

CLI options: `audio-loudness-normalizer input [output] [--target LUFS] [--ceiling dBFS] [--measure]`. Defaults are `--target -23.0` and `--ceiling -1.0`. Exit codes: 0 success, 1 silent or too-short input, 2 usage, I/O, or unsupported-format error.

## Why not pyloudnorm or ffmpeg loudnorm

This package has no NumPy, SciPy, or binary dependency, and every measurement constant is traceable to ITU-R BS.1770-4 or its documented bilinear-transform derivation.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Security](docs/SECURITY.md)

## License

MIT
