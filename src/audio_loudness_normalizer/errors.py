"""Error types for audio loudness normalization."""

from __future__ import annotations

from typing import Literal

ErrorCode = Literal[
    "too_short",
    "unsupported_format",
    "input_too_long",
    "silent",
    "invalid_wav",
    "invalid_target",
]


class LoudnessError(Exception):
    """Base error for the audio_loudness_normalizer package.

    Attributes:
        code: Machine-readable error code.
    """

    def __init__(self, code: ErrorCode, message: str = "") -> None:
        self.code = code
        if len(message) > 200:
            message = message[:197] + "..."
        super().__init__(message)
