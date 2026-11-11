# Security

This library processes untrusted audio data. Security considerations are limited to safe parsing of WAV files and avoiding resource exhaustion.

## Threat Model

### Defended

- `read_wav` accepts only uncompressed PCM 16-bit WAV with 1 or 2 channels.
- `read_wav` rejects sample rates outside 8000-192000 Hz with `unsupported_format`.
- `read_wav` checks the declared duration against `max_seconds` (default 600.0) and raises `input_too_long` before reading frames.
- `read_wav` rejects incomplete frame data, sample-width mismatch, and sample-count mismatch with `invalid_wav`.
- `normalize` rejects targets outside `[-70, 0]` and peak ceilings above 0 dBFS with `invalid_target`.
- `normalize` rejects audio shorter than 0.4 s with `too_short` and silent or below-gate input with `silent`.
- `LoudnessError` messages are truncated to at most 200 characters.

### Not defended

- The library receives `bytes`; it does not bound memory already allocated by the caller before `read_wav` is called.
- The CLI reads the entire input file into memory before calling `read_wav`; `max_seconds` limits decoded duration, not the size of the file on disk.
- The library does not open paths itself; the CLI opens the paths supplied by the caller, so path validation and filesystem permissions are the caller's responsibility.
- The peak ceiling is a sample-peak ceiling, not a true-peak ceiling; inter-sample peaks are not measured.
- `write_wav` clips converted samples to the int16 range and does not apply dither.
- The library does not provide authentication, authorization, sandboxing, or reporting of sensitive input content.

## Recommendations

- Set a smaller `max_seconds` when processing untrusted inputs.
- Bound file size before reading input bytes, especially when using the CLI.
- Validate file paths and filesystem permissions when calling the CLI.
- Do not treat `peak_ceiling_dbfs` as a true-peak guarantee.
