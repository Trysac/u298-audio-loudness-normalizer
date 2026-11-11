# Architecture

## Purpose

`trysac-audio-loudness-normalizer` is a small, dependency-free Python library: Measure integrated loudness per ITU-R BS.1770-4 with K-weighting and gating, then normalize PCM WAV audio to a LUFS target with a sample-peak ceiling, in pure Python

## Shape

```text
caller code --> audio_loudness_normalizer (public API in __init__.py)
                    |
                    +-- pure functions, no I/O, no global state
```

- **Public API**: the names listed in `__all__` of `src/audio_loudness_normalizer/__init__.py`. Anything else is
  internal and may change without a major version.
- **Errors**: invalid input raises built-in exceptions (`ValueError`, `TypeError`) with a clear
  message; the library never prints or exits.
- **Side effects**: none. If a feature needs I/O, isolate it in its own module behind a small
  interface and record the choice in an ADR.

## Quality contract

`scripts/check.py` is the single definition of the gates; `fabrica.json` tells the factory and CI
how to run it. See [TESTING.md](TESTING.md).

## Decisions

Architecture decisions are recorded in [decisions/](decisions/) as numbered ADRs.
