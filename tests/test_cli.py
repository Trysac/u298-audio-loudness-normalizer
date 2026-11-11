"""Tests for the command-line interface."""

from __future__ import annotations

import math
import wave

from audio_loudness_normalizer.__main__ import main


def _make_wav(
    rate: int, duration: float, amplitude: float, channels: int = 1, filename: str = "test.wav"
) -> str:
    """Create a WAV file on disk and return its path."""
    num_samples = int(rate * duration)
    if channels == 1:
        samples = [amplitude * math.sin(2 * math.pi * 1000 * i / rate) for i in range(num_samples)]
        raw = bytearray()
        for s in samples:
            val = round(s * 32767)
            raw.extend(val.to_bytes(2, byteorder="little", signed=True))
    else:
        left = [amplitude * math.sin(2 * math.pi * 1000 * i / rate) for i in range(num_samples)]
        right = left[:]
        raw = bytearray()
        for left_s, right_s in zip(left, right, strict=True):
            for s in (left_s, right_s):
                val = round(s * 32767)
                raw.extend(val.to_bytes(2, byteorder="little", signed=True))
    with wave.open(filename, "wb") as wav:
        wav.setnchannels(channels)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(raw)
    return filename


def test_main_measure(capsys, tmp_path):
    in_path = tmp_path / "in.wav"
    _make_wav(48000, 3.0, 10 ** (-23 / 20), channels=2, filename=str(in_path))
    exit_code = main([str(in_path), "--measure"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "integrated -23.0 LUFS" in captured.out


def test_main_normalize(capsys, tmp_path):
    in_path = tmp_path / "in.wav"
    out_path = tmp_path / "out.wav"
    _make_wav(48000, 3.0, 10 ** (-23 / 20), channels=2, filename=str(in_path))
    exit_code = main([str(in_path), str(out_path), "--target", "-16"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "measured -23.0 LUFS, gain +7.0 dB" in captured.out
    assert out_path.exists()


def test_main_missing_file(capsys):
    exit_code = main(["nonexistent.wav", "--measure"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "Error reading" in captured.err


def test_main_silent_input(capsys, tmp_path):
    in_path = tmp_path / "silent.wav"
    _make_wav(48000, 1.0, 0.0, channels=1, filename=str(in_path))
    exit_code = main([str(in_path), "--measure"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "silent" in captured.err


def test_main_too_short(capsys, tmp_path):
    in_path = tmp_path / "short.wav"
    _make_wav(48000, 0.1, 0.1, channels=1, filename=str(in_path))
    exit_code = main([str(in_path), "--measure"])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert "too short" in captured.err


def test_main_unsupported_format(capsys, tmp_path):
    # Create a 24-bit WAV file on disk.
    in_path = tmp_path / "bad.wav"
    with wave.open(str(in_path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(3)
        wav.setframerate(8000)
        wav.writeframes(b"\x00\x00\x00" * 100)
    exit_code = main([str(in_path), "--measure"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "unsupported" in captured.err
