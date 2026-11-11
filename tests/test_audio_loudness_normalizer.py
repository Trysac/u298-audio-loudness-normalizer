"""Behavior tests for the public API of audio_loudness_normalizer."""

from __future__ import annotations

import math

import pytest

import audio_loudness_normalizer


def test_public_api_exports() -> None:
    for name in (
        "Audio",
        "LoudnessError",
        "NormalizeResult",
        "integrated_loudness",
        "k_weighting",
        "normalize",
        "read_wav",
        "write_wav",
    ):
        assert hasattr(audio_loudness_normalizer, name)


def test_normalize_round_trip() -> None:
    rate = 48000
    duration = 3.0
    amplitude = 10 ** (-23 / 20)
    num_samples = round(rate * duration)
    left = tuple(amplitude * math.sin(2 * math.pi * 1000 * i / rate) for i in range(num_samples))
    audio = audio_loudness_normalizer.Audio(rate=rate, channels=(left, left))

    result = audio_loudness_normalizer.normalize(audio, target_lufs=-16.0)
    assert not result.peak_limited
    assert result.gain_db == pytest.approx(7.0, abs=0.1)
    assert audio_loudness_normalizer.integrated_loudness(result.audio) == pytest.approx(
        -16.0, abs=0.1
    )


def test_version_is_semver() -> None:
    parts = audio_loudness_normalizer.__version__.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)
