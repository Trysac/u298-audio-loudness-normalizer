# audio-loudness-normalizer

[![PyPI version](https://img.shields.io/pypi/v/trysac-audio-loudness-normalizer)](https://pypi.org/project/trysac-audio-loudness-normalizer/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-audio-loudness-normalizer)](LICENSE)
[![CI](https://github.com/Trysac/u298-audio-loudness-normalizer/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u298-audio-loudness-normalizer/actions/workflows/ci.yml)

Measure integrated loudness per ITU-R BS.1770-4 with K-weighting and gating, then normalize PCM WAV audio to a LUFS target with a sample-peak ceiling, in pure Python

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-audio-loudness-normalizer
# or
uv add trysac-audio-loudness-normalizer
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import audio_loudness_normalizer

# normalize() trims surrounding whitespace and lower-cases the text.
print(audio_loudness_normalizer.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    audio_loudness_normalizer.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
