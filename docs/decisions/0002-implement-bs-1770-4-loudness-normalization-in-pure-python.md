# Implement BS.1770-4 loudness normalization in pure Python

Status: accepted (generated, pending human review)

## Context

The repository needs an audio loudness normalization utility that follows ITU-R BS.1770-4 exactly, without external dependencies. The specification requires accurate K-weighting, gated loudness measurement, and normalization with a peak ceiling.

## Decision

Implement the algorithm using only the Python standard library (wave, math, array). For 48 kHz, use the exact table coefficients from the standard; for other rates, use a well-documented bilinear transform derivation. The public API consists of dataclasses and functions for reading/writing WAV, computing filters, measuring loudness, and normalizing.

## Consequences

The library is dependency-free and portable. Performance is acceptable for typical audio durations due to pure Python loops. The implementation is thoroughly tested against EBU Tech 3341 test cases and edge cases.
