"""Core implementation of BS.1770-4 loudness measurement and normalization."""

from __future__ import annotations

import array
import io
import logging
import math
import wave
from dataclasses import dataclass

from audio_loudness_normalizer.errors import LoudnessError

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

# Type alias for biquad coefficients: (b, a) where each is a list of floats.
Biquad = tuple[list[float], list[float]]


@dataclass(frozen=True)
class Audio:
    """Frozen dataclass representing PCM audio.

    Attributes:
        rate: Sample rate in Hz.
        channels: Tuple of channels; each channel is a tuple of float samples
            in the range [-1.0, 1.0].
    """

    rate: int
    channels: tuple[tuple[float, ...], ...]

    def __post_init__(self) -> None:
        if not self.channels:
            raise ValueError("Audio must have at least one channel")
        if len(self.channels) not in (1, 2):
            raise ValueError("Audio supports 1 or 2 channels only")
        first_len = len(self.channels[0])
        if any(len(ch) != first_len for ch in self.channels):
            raise ValueError("All channels must have the same length")
        if first_len == 0:
            raise ValueError("Audio channels cannot be empty")


@dataclass(frozen=True)
class NormalizeResult:
    """Result of loudness normalization.

    Attributes:
        audio: The normalized audio.
        measured_lufs: Measured integrated loudness of the input before gain.
        gain_db: Applied gain in dB.
        peak_limited: True if gain was reduced to respect the peak ceiling.
    """

    audio: Audio
    measured_lufs: float
    gain_db: float
    peak_limited: bool


def read_wav(data: bytes, *, max_seconds: float = 600.0) -> Audio:
    """Parse a WAV file from bytes.

    The WAV must be uncompressed PCM, 16-bit, with 1 or 2 channels.
    Sample rate must be between 8000 and 192000 Hz.

    Args:
        data: WAV file content.
        max_seconds: Maximum allowed duration in seconds.

    Returns:
        Audio object with samples normalized to [-1.0, 1.0].

    Raises:
        LoudnessError: If the WAV is invalid, unsupported, or too long.
    """
    try:
        with wave.open(io.BytesIO(data), "rb") as wav:
            nchannels = wav.getnchannels()
            sampwidth = wav.getsampwidth()
            comptype = wav.getcomptype()
            framerate = wav.getframerate()
            nframes = wav.getnframes()

            if nchannels not in (1, 2):
                raise LoudnessError("unsupported_format", "Only mono or stereo supported")
            if sampwidth != 2:
                raise LoudnessError("unsupported_format", "Only 16-bit PCM supported")
            if comptype != "NONE":
                raise LoudnessError("unsupported_format", "Only uncompressed PCM supported")
            if not (8000 <= framerate <= 192000):
                raise LoudnessError("unsupported_format", "Sample rate outside 8000-192000 Hz")
            duration = nframes / framerate
            if duration > max_seconds:
                raise LoudnessError("input_too_long", f"Audio longer than {max_seconds} seconds")

            raw_frames = wav.readframes(nframes)
            if len(raw_frames) != nframes * nchannels * sampwidth:
                raise LoudnessError("invalid_wav", "Incomplete frame data")

            # Convert raw bytes to int16 samples.
            samples_int = array.array("h")
            samples_int.frombytes(raw_frames)
            if samples_int.itemsize != 2:
                raise LoudnessError("invalid_wav", "Sample width mismatch")
            total_samples = len(samples_int)
            if total_samples != nframes * nchannels:
                raise LoudnessError("invalid_wav", "Sample count mismatch")

            # Convert to float in [-1.0, 1.0]
            samples_float = [s / 32768.0 for s in samples_int]

            channels: tuple[tuple[float, ...], ...]
            if nchannels == 1:
                channels = (tuple(samples_float),)
            else:
                left = tuple(samples_float[0::2])
                right = tuple(samples_float[1::2])
                channels = (left, right)

            return Audio(rate=framerate, channels=channels)
    except (wave.Error, EOFError) as e:
        raise LoudnessError("invalid_wav", f"Error reading WAV: {e}") from e


def write_wav(audio: Audio) -> bytes:
    """Encode Audio to WAV bytes (PCM 16-bit, uncompressed).

    Samples are converted with round(x * 32767) using half-to-even rounding,
    then clipped to the range [-32768, 32767].

    Args:
        audio: Audio to encode.

    Returns:
        WAV file content as bytes.
    """
    if len(audio.channels) not in (1, 2):
        raise LoudnessError("unsupported_format", "Only mono or stereo supported")
    if not (8000 <= audio.rate <= 192000):
        raise LoudnessError("unsupported_format", "Sample rate outside 8000-192000 Hz")

    nchannels = len(audio.channels)

    # Flatten interleaved samples.
    if nchannels == 1:
        flat = list(audio.channels[0])
    else:
        flat = []
        for left_s, right_s in zip(audio.channels[0], audio.channels[1], strict=True):
            flat.extend([left_s, right_s])

    int_samples = []
    for s in flat:
        # Round half to even, then clip.
        val = round(s * 32767)
        if val > 32767:
            val = 32767
        elif val < -32768:
            val = -32768
        int_samples.append(val)

    arr = array.array("h", int_samples)
    raw = arr.tobytes()

    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(nchannels)
            wav.setsampwidth(2)
            wav.setframerate(audio.rate)
            wav.writeframes(raw)
        return buf.getvalue()


def k_weighting(rate: int) -> tuple[Biquad, Biquad]:
    """Return the two K-weighting biquad filters for the given sample rate.

    For 48 kHz the exact BS.1770-4 Annex 1 coefficients are returned.
    For other rates between 8000 and 192000 Hz, the bilinear transform
    derivation from the reference implementation is used.

    Args:
        rate: Sample rate in Hz. Must be between 8000 and 192000.

    Returns:
        A tuple of (shelf_filter, highpass_filter), each represented as
        (b_coefficients, a_coefficients).

    Raises:
        LoudnessError: If rate is outside the supported range.
    """
    if not (8000 <= rate <= 192000):
        raise LoudnessError("unsupported_format", "Sample rate outside 8000-192000 Hz")

    if rate == 48000:
        # Exact table coefficients from ITU-R BS.1770-4, Annex 1, Tables 1 and 2.
        shelf: Biquad = (
            [1.53512485958697, -2.69169618940638, 1.19839281085285],
            [1.0, -1.69065929318241, 0.73248077421585],
        )
        highpass: Biquad = (
            [1.0, -2.0, 1.0],
            [1.0, -1.99004745483398, 0.99007225036621],
        )
        return shelf, highpass

    # Derivation for other rates using bilinear transform.
    # Stage 1: high shelf
    f0_shelf = 1681.974450955533
    G_db = 3.999843853973347
    Q_shelf = 0.7071752369554196
    K = math.tan(math.pi * f0_shelf / rate)
    Vh = 10 ** (G_db / 20)
    Vb = Vh**0.4996667741545416
    a0 = 1 + K / Q_shelf + K * K
    b0 = (Vh + Vb * K / Q_shelf + K * K) / a0
    b1 = 2 * (K * K - Vh) / a0
    b2 = (Vh - Vb * K / Q_shelf + K * K) / a0
    a1 = 2 * (K * K - 1) / a0
    a2 = (1 - K / Q_shelf + K * K) / a0
    shelf = ([b0, b1, b2], [1.0, a1, a2])

    # Stage 2: high-pass
    f0_hp = 38.13547087602444
    Q_hp = 0.5003270373238773
    K = math.tan(math.pi * f0_hp / rate)
    d = 1 + K / Q_hp + K * K
    b_hp = [1.0, -2.0, 1.0]
    a1_hp = 2 * (K * K - 1) / d
    a2_hp = (1 - K / Q_hp + K * K) / d
    highpass = (b_hp, [1.0, a1_hp, a2_hp])

    return shelf, highpass


def _apply_biquad(samples: list[float], b: list[float], a: list[float]) -> list[float]:
    """Apply a biquad filter in direct form I from zero state."""
    x1 = 0.0
    x2 = 0.0
    y1 = 0.0
    y2 = 0.0
    result = []
    b0, b1, b2 = b
    a1, a2 = a[1], a[2]  # a[0] assumed 1
    for x in samples:
        y = b0 * x + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
        result.append(y)
        x2 = x1
        x1 = x
        y2 = y1
        y1 = y
    return result


def integrated_loudness(audio: Audio) -> float:
    """Compute integrated loudness in LUFS according to ITU-R BS.1770-4.

    Args:
        audio: Audio to measure.

    Returns:
        Integrated loudness value in LUFS. If no block passes the gates
        (e.g., silence or too short), returns float('-inf').
    """
    rate = audio.rate
    channels = audio.channels

    # Apply K-weighting to each channel.
    shelf, highpass = k_weighting(rate)
    filtered_channels = []
    for ch in channels:
        stage1 = _apply_biquad(list(ch), shelf[0], shelf[1])
        stage2 = _apply_biquad(stage1, highpass[0], highpass[1])
        filtered_channels.append(stage2)

    block_size = round(0.4 * rate)
    hop_size = round(0.1 * rate)
    num_samples = len(filtered_channels[0])

    # Compute block energies and gate them.
    block_starts = list(range(0, num_samples - block_size + 1, hop_size))
    if not block_starts:
        return float("-inf")

    # For each block, compute z (sum of mean squares across channels).
    block_z_list = []
    for start in block_starts:
        end = start + block_size
        total_sq = 0.0
        for fc in filtered_channels:
            block = fc[start:end]
            mean_sq = sum(x * x for x in block) / block_size
            total_sq += mean_sq  # G_i = 1 for all channels
        block_z_list.append(total_sq)

    # Absolute gate: keep blocks with loudness > -70 LUFS.
    kept_z = []
    for z in block_z_list:
        if z > 0:
            loudness = -0.691 + 10 * math.log10(z)
            if loudness > -70.0:
                kept_z.append(z)
    if not kept_z:
        return float("-inf")

    # Relative gate: threshold = loudness of mean z of kept blocks - 10 LU.
    mean_z = sum(kept_z) / len(kept_z)
    rel_threshold = (-0.691 + 10 * math.log10(mean_z)) - 10.0
    final_z = []
    for z in kept_z:
        loudness = -0.691 + 10 * math.log10(z)
        if loudness > rel_threshold:
            final_z.append(z)
    if not final_z:
        return float("-inf")

    mean_z_final = sum(final_z) / len(final_z)
    integrated = -0.691 + 10 * math.log10(mean_z_final)
    return integrated


def normalize(
    audio: Audio,
    *,
    target_lufs: float = -23.0,
    peak_ceiling_dbfs: float = -1.0,
) -> NormalizeResult:
    """Normalize audio to a target loudness with peak ceiling.

    Args:
        audio: Input audio.
        target_lufs: Target integrated loudness in LUFS. Must be in [-70, 0].
        peak_ceiling_dbfs: Maximum allowed sample peak level in dBFS. Must be <= 0.

    Returns:
        NormalizeResult containing the normalized audio, measured loudness,
        applied gain, and whether peak limiting occurred.

    Raises:
        LoudnessError: If target or ceiling invalid, audio too short, or silent.
    """
    if not (-70.0 <= target_lufs <= 0.0):
        raise LoudnessError("invalid_target", "target_lufs must be between -70 and 0")
    if peak_ceiling_dbfs > 0.0:
        raise LoudnessError("invalid_target", "peak_ceiling_dbfs must be <= 0")

    rate = audio.rate
    num_samples = len(audio.channels[0])
    block_size = round(0.4 * rate)
    if num_samples < block_size:
        raise LoudnessError("too_short", "Audio shorter than 0.4 seconds")

    measured_lufs = integrated_loudness(audio)
    if measured_lufs == float("-inf"):
        raise LoudnessError("silent", "Input is silent or below gating threshold")

    gain_db = target_lufs - measured_lufs

    # Compute original peak amplitude across all samples.
    max_abs = 0.0
    for ch in audio.channels:
        for s in ch:
            a = abs(s)
            if a > max_abs:
                max_abs = a

    # If original peak is 0, can't compute dB; treat as silent.
    if max_abs == 0.0:
        raise LoudnessError("silent", "Input is digital silence")

    peak_limited = False
    # Check if applying the desired gain would exceed the peak ceiling.
    linear_gain = 10 ** (gain_db / 20)
    peak_after_gain_dbfs = 20 * math.log10(max_abs * linear_gain)
    if peak_after_gain_dbfs > peak_ceiling_dbfs:
        peak_limited = True
        gain_db = peak_ceiling_dbfs - 20 * math.log10(max_abs)
        linear_gain = 10 ** (gain_db / 20)

    # Apply gain and clip to [-1, 1] for safety.
    new_channels = []
    for ch in audio.channels:
        new_ch = []
        for s in ch:
            ns = s * linear_gain
            if ns > 1.0:
                ns = 1.0
            elif ns < -1.0:
                ns = -1.0
            new_ch.append(ns)
        new_channels.append(tuple(new_ch))
    new_audio = Audio(rate=audio.rate, channels=tuple(new_channels))

    return NormalizeResult(
        audio=new_audio,
        measured_lufs=measured_lufs,
        gain_db=gain_db,
        peak_limited=peak_limited,
    )
