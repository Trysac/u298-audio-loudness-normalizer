"""Audio loudness measurement and normalization per ITU-R BS.1770-4.

This package provides tools to measure integrated loudness of PCM WAV audio
and apply gain to normalize it to a target LUFS value, respecting a sample
peak ceiling.
"""

from audio_loudness_normalizer.core import (
    Audio,
    NormalizeResult,
    integrated_loudness,
    k_weighting,
    normalize,
    read_wav,
    write_wav,
)
from audio_loudness_normalizer.errors import LoudnessError

__all__ = [
    "Audio",
    "LoudnessError",
    "NormalizeResult",
    "integrated_loudness",
    "k_weighting",
    "normalize",
    "read_wav",
    "write_wav",
]

__version__ = "0.1.0"
