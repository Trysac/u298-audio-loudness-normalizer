# Testing

## Running

```sh
uv run pytest
```

The tests use pytest and the standard library. The supplied tree contains two test files: `tests/test_audio_loudness_normalizer.py` and `tests/test_cli.py`.

## Policy

The tests assert observable behavior: public exports, measured loudness, normalization gain and flags, written WAV data, printed CLI output, exit codes, and `LoudnessError` codes. CLI tests generate WAV data under pytest's `tmp_path` and capture output with `capsys`. The tests do not use network access.

## Tiers

There is one local pytest suite. The supplied repository does not contain conformance markers, external-tool setup scripts, or a separate CI-only test tier.

## Layout

- `tests/test_audio_loudness_normalizer.py` contains `test_public_api_exports`, `test_normalize_round_trip`, and `test_version_is_semver`. It checks the exported names, normalization and WAV round-trip behavior, and the semantic version string.
- `tests/test_cli.py` contains `test_main_measure`, `test_main_normalizer`, `test_main_missing_file`, `test_main_silent_input`, `test_main_too_short`, and `test_main_unsupported_format`, with a `_make_wav` helper. It checks CLI measurement output, normalization and output writing, missing-file handling, silent input, too-short input, and unsupported format handling.
- No `tests/conftest.py` is present in the supplied tree.
