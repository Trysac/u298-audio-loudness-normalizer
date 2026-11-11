"""Tests for audio_loudness_normalizer.core."""

from __future__ import annotations

import array
import io
import math
import wave

import pytest

from audio_loudness_normalizer.core import (
    Audio,
    integrated_loudness,
    k_weighting,
    normalize,
    read_wav,
    write_wav,
)
from audio_loudness_normalizer.errors import LoudnessError

# Helper functions


def _make_sine_wav(
    rate: int, duration: float, amplitude: float, channels: int = 1, freq: float = 1000.0
) -> bytes:
    """Generate a WAV file containing sine waves of given amplitude."""
    num_samples = round(rate * duration)
    if channels == 1:
        samples = [amplitude * math.sin(2 * math.pi * freq * i / rate) for i in range(num_samples)]
        int_samples = [round(s * 32767) for s in samples]
        raw = array.array("h", int_samples).tobytes()
    else:
        left = [amplitude * math.sin(2 * math.pi * freq * i / rate) for i in range(num_samples)]
        right = left[:]  # same signal for simplicity
        flat = []
        for left_s, right_s in zip(left, right, strict=True):
            flat.extend([left_s, right_s])
        int_samples = [round(s * 32767) for s in flat]
        raw = array.array("h", int_samples).tobytes()

    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(channels)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            wav.writeframes(raw)
        return buf.getvalue()


def _make_audio_from_samples(channels: list[list[float]], rate: int = 48000) -> Audio:
    """Create Audio from lists of samples."""
    return Audio(rate=rate, channels=tuple(tuple(ch) for ch in channels))


# Tests for k_weighting


def test_k_weighting_48k_table():
    shelf, highpass = k_weighting(48000)
    assert shelf[0] == pytest.approx(
        [1.53512485958697, -2.69169618940638, 1.19839281085285], abs=1e-9
    )
    assert shelf[1] == pytest.approx([1.0, -1.69065929318241, 0.73248077421585], abs=1e-9)
    assert highpass[0] == pytest.approx([1.0, -2.0, 1.0], abs=1e-9)
    assert highpass[1] == pytest.approx([1.0, -1.99004745483398, 0.99007225036621], abs=1e-9)


def test_k_weighting_other_rate():
    # Just ensure it runs without error and coefficients are finite floats.
    shelf, highpass = k_weighting(44100)
    assert all(isinstance(x, float) for x in shelf[0] + shelf[1] + highpass[0] + highpass[1])
    assert len(shelf[0]) == 3 and len(shelf[1]) == 3


def test_k_weighting_invalid_rate():
    with pytest.raises(LoudnessError) as exc:
        k_weighting(7999)
    assert exc.value.code == "unsupported_format"
    with pytest.raises(LoudnessError) as exc:
        k_weighting(192001)
    assert exc.value.code == "unsupported_format"


# Tests for read_wav and write_wav


def test_read_wav_mono():
    rate = 8000
    data = _make_sine_wav(rate, 0.5, 0.5, channels=1)
    audio = read_wav(data)
    assert audio.rate == rate
    assert len(audio.channels) == 1
    assert len(audio.channels[0]) == rate // 2  # 0.5 sec


def test_read_wav_stereo():
    rate = 44100
    data = _make_sine_wav(rate, 0.1, 0.5, channels=2)
    audio = read_wav(data)
    assert audio.rate == rate
    assert len(audio.channels) == 2
    assert len(audio.channels[0]) == len(audio.channels[1])
    assert len(audio.channels[0]) == round(rate * 0.1)


def test_read_wav_invalid_channels():
    # Create a 3-channel WAV.
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(3)
            wav.setsampwidth(2)
            wav.setframerate(8000)
            wav.writeframes(b"\x00\x00" * 300)
        data = buf.getvalue()
    with pytest.raises(LoudnessError) as exc:
        read_wav(data)
    assert exc.value.code == "unsupported_format"


def test_read_wav_invalid_sampwidth():
    # 24-bit WAV.
    with io.BytesIO() as buf:
        with wave.open(buf, "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(3)
            wav.setframerate(8000)
            wav.writeframes(b"\x00\x00\x00" * 100)
        data = buf.getvalue()
    with pytest.raises(LoudnessError) as exc:
        read_wav(data)
    assert exc.value.code == "unsupported_format"


def test_read_wav_too_long():
    rate = 8000
    # 601 seconds
    duration = 601
    data = _make_sine_wav(rate, duration, 0.1)
    with pytest.raises(LoudnessError) as exc:
        read_wav(data, max_seconds=600.0)
    assert exc.value.code == "input_too_long"


def test_read_wav_invalid_data():
    with pytest.raises(LoudnessError) as exc:
        read_wav(b"not a wav")
    assert exc.value.code == "invalid_wav"


def test_write_wav_roundtrip():
    # Generate known int16 samples.
    samples = [0, 1, -1, 32767, -32768]
    expected = [0, 1, -1, 32767, -32767]  # -32768 becomes -32767 (write uses *32767)
    audio = Audio(rate=8000, channels=(tuple(s / 32768.0 for s in samples),))
    wav_bytes = write_wav(audio)
    back = read_wav(wav_bytes)
    assert back.rate == 8000
    assert back.channels[0] == pytest.approx([s / 32768.0 for s in expected], abs=1 / 32768)
    # Additionally assert on the WAV header.
    with io.BytesIO(wav_bytes) as buf, wave.open(buf, "rb") as wav:
        assert wav.getnchannels() == 1
        assert wav.getsampwidth() == 2
        assert wav.getframerate() == 8000


def test_write_wav_clipping():
    audio = Audio(rate=8000, channels=((2.0, -2.0),))
    wav_bytes = write_wav(audio)
    audio2 = read_wav(wav_bytes)
    # Clipped to max/min
    assert audio2.channels[0][0] == pytest.approx(32767 / 32768.0)
    assert audio2.channels[0][1] == pytest.approx(-32768 / 32768.0)


# Tests for integrated_loudness


def test_integrated_loudness_stereo_sine_48k():
    rate = 48000
    duration = 3.0
    amplitude = 10 ** (-23 / 20)
    data = _make_sine_wav(rate, duration, amplitude, channels=2)
    audio = read_wav(data)
    loudness = integrated_loudness(audio)
    assert loudness == pytest.approx(-23.0, abs=0.1)


def test_integrated_loudness_mono_sine_48k():
    rate = 48000
    duration = 3.0
    amplitude = 10 ** (-23 / 20)
    data = _make_sine_wav(rate, duration, amplitude, channels=1)
    audio = read_wav(data)
    loudness = integrated_loudness(audio)
    assert loudness == pytest.approx(-26.0, abs=0.1)


def test_integrated_loudness_sine_then_silence():
    rate = 48000
    duration_sine = 3.0
    duration_silence = 3.0
    total_samples = round(rate * (duration_sine + duration_silence))
    sine_samples = round(rate * duration_sine)
    amplitude = 10 ** (-23 / 20)
    samples = []
    for i in range(total_samples):
        if i < sine_samples:
            samples.append(amplitude * math.sin(2 * math.pi * 1000 * i / rate))
        else:
            samples.append(0.0)
    audio = Audio(rate=rate, channels=(tuple(samples), tuple(samples)))
    loudness = integrated_loudness(audio)
    # Expected approximately -23.22 according to spec.
    assert loudness == pytest.approx(-23.22, abs=0.05)


def test_integrated_loudness_silence():
    rate = 48000
    duration = 1.0
    samples = [0.0] * round(rate * duration)
    audio = Audio(rate=rate, channels=(tuple(samples),))
    assert integrated_loudness(audio) == float("-inf")


def test_integrated_loudness_dc_offset_removed():
    rate = 8000
    duration = 1.0
    samples = [0.5] * round(rate * duration)  # constant DC
    audio = Audio(rate=rate, channels=(tuple(samples),))
    # The high-pass filter removes the DC offset; only the filter's start-up
    # transient remains, so the result is far below the raw DC level (~-6.7 LUFS).
    assert integrated_loudness(audio) < -30.0


def test_integrated_loudness_44100():
    rate = 44100
    duration = 3.0
    amplitude = 10 ** (-23 / 20)
    data = _make_sine_wav(rate, duration, amplitude, channels=2)
    audio = read_wav(data)
    loudness = integrated_loudness(audio)
    assert loudness == pytest.approx(-23.0, abs=0.1)


def test_integrated_loudness_too_short():
    rate = 48000
    duration = 0.1  # shorter than 0.4s
    samples = [0.1] * round(rate * duration)
    audio = Audio(rate=rate, channels=(tuple(samples),))
    assert integrated_loudness(audio) == float("-inf")


def test_integrated_loudness_exactly_one_block():
    rate = 48000
    num_samples = round(0.4 * rate)  # 19200 samples -> exactly one block
    amplitude = 10 ** (-23 / 20)
    samples = tuple(amplitude * math.sin(2 * math.pi * 1000 * i / rate) for i in range(num_samples))
    audio = Audio(rate=rate, channels=(samples,))
    assert integrated_loudness(audio) == pytest.approx(-26.0, abs=0.2)
    result = normalize(audio)
    assert result.measured_lufs == pytest.approx(-26.0, abs=0.2)


def test_integrated_loudness_minus80dbfs():
    rate = 48000
    duration = 3.0
    amplitude = 10 ** (-80 / 20)
    data = _make_sine_wav(rate, duration, amplitude, channels=2)
    audio = read_wav(data)
    loudness = integrated_loudness(audio)
    assert loudness == float("-inf")


# Tests for normalize


def test_normalize_to_target():
    rate = 48000
    duration = 3.0
    amplitude = 10 ** (-23 / 20)
    data = _make_sine_wav(rate, duration, amplitude, channels=2)
    audio = read_wav(data)
    result = normalize(audio, target_lufs=-16.0)
    assert not result.peak_limited
    assert result.gain_db == pytest.approx(7.0, abs=0.1)
    assert result.measured_lufs == pytest.approx(-23.0, abs=0.1)
    # Check output loudness
    out_loudness = integrated_loudness(result.audio)
    assert out_loudness == pytest.approx(-16.0, abs=0.1)


def test_normalize_peak_limited():
    rate = 48000
    duration = 3.0
    amplitude = 10 ** (-23 / 20)
    num_samples = round(rate * duration)
    left = tuple(amplitude * math.sin(2 * math.pi * 1000 * i / rate) for i in range(num_samples))
    audio = Audio(rate=rate, channels=(left, left))
    result = normalize(audio, target_lufs=0.0, peak_ceiling_dbfs=-1.0)
    assert result.peak_limited
    assert result.gain_db == pytest.approx(22.0, abs=1e-9)
    assert result.measured_lufs == pytest.approx(-23.0, abs=0.1)


def test_normalize_too_short():
    rate = 48000
    duration = 0.1
    samples = [0.1] * round(rate * duration)
    audio = Audio(rate=rate, channels=(tuple(samples),))
    with pytest.raises(LoudnessError) as exc:
        normalize(audio)
    assert exc.value.code == "too_short"


def test_normalize_silent():
    rate = 48000
    duration = 1.0
    samples = [0.0] * round(rate * duration)
    audio = Audio(rate=rate, channels=(tuple(samples),))
    with pytest.raises(LoudnessError) as exc:
        normalize(audio)
    assert exc.value.code == "silent"


def test_normalize_invalid_target():
    audio = Audio(rate=48000, channels=((0.1,) * 48000,))  # 1 sec
    with pytest.raises(LoudnessError) as exc:
        normalize(audio, target_lufs=-71.0)
    assert exc.value.code == "invalid_target"
    with pytest.raises(LoudnessError) as exc:
        normalize(audio, target_lufs=0.1)
    assert exc.value.code == "invalid_target"
    with pytest.raises(LoudnessError) as exc:
        normalize(audio, peak_ceiling_dbfs=0.1)
    assert exc.value.code == "invalid_target"
