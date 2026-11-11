# Project record

## Objective

Measure integrated loudness per ITU-R BS.1770-4 with K-weighting and gating, then normalize PCM WAV audio to a LUFS target with a sample-peak ceiling, in pure Python.

## Scope

The project provides:

- Integrated loudness measurement with the BS.1770-4 K-weighting filters, 0.4 s blocks with 75 % overlap, the -70 LUFS absolute gate, and the relative gate 10 LU below the mean of the absolute-gated blocks.
- Loudness normalization by gain to a target LUFS value, reduced when needed to keep the sample peak below the requested ceiling.
- Parsing and writing uncompressed PCM 16-bit WAV, mono or stereo, at sample rates from 8000 to 192000 Hz.
- The public Python API and command-line interface documented in [README.md](../README.md), with typed inputs and machine-readable `LoudnessError` codes.

Out of scope:

- True-peak measurement (oversampling).
- Loudness range, short-term loudness, and momentary loudness.
- More than two channels.
- Resampling.
- MP3 or other codecs.

## Timeline

No dated milestones are recorded in the specification.

## Effort metrics

Measured values only; a value that has not been measured stays "pending measurement".

| Metric | Value |
|---|---|
| Tokens (input / output) | 1111437 / 82125 |
| Hours (human) | pending measurement |
| Cost (USD) | 0.1806 |

## Factory run u298 (measured from API usage)

| Date (UTC) | Phase | Model | Batch | Input | Output | Cache write | Cache read | Cost (USD) |
|---|---|---|---|---|---|---|---|---|
| 2026-11-11 | generation | deepseek-v4-pro | yes | 2037 | 18271 | 0 | 3328 | 0.0376 |
| 2026-11-11 | fix-1 | deepseek-v4-pro | no | 37741 | 27337 | 0 | 535040 | 0.0908 |
| 2026-11-11 | audit | deepseek-flash | no | 19778 | 27013 | 0 | 344192 | 0.0202 |
| 2026-11-11 | fix-2 | deepseek-v4-pro | no | 13428 | 1274 | 0 | 59648 | 0.0127 |
| 2026-11-11 | docs | deepseek-flash | no | 95989 | 8230 | 0 | 256 | 0.0193 |

Total: $0.1806. Prices: deepseek line, as measured by its adapter. Providers serve the current version of each model id, so the date tells which version answered; versions, launch stages and price sources per line are in the factory's model register (docs/MODELS.md).
