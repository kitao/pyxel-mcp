"""Tests for _audio module."""

import math
import struct
import tempfile
import wave

import numpy as np
import pytest

from pyxel_mcp._common.audio import (
    freq_to_note, freq_to_midi, estimate_freq,
    detect_key, analyze_intervals, suggest_role,
    analyze_wav,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_wav(path, samples_int16, sample_rate=44100, n_channels=1):
    """Write int16 samples to a WAV file."""
    with wave.open(path, "w") as wf:
        wf.setnchannels(n_channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(samples_int16.tobytes())


def _sine_samples(freq, duration_s, sample_rate=44100, amplitude=16000):
    """Generate int16 sine wave samples."""
    t = np.arange(int(sample_rate * duration_s)) / sample_rate
    return (np.sin(2 * np.pi * freq * t) * amplitude).astype(np.int16)

def test_freq_to_note_a4():
    assert freq_to_note(440.0) == "A4"

def test_freq_to_note_c4():
    assert freq_to_note(261.63) == "C4"

def test_freq_to_note_silence():
    assert freq_to_note(0) == "~"
    assert freq_to_note(10) == "~"

def test_freq_to_midi_a4():
    assert freq_to_midi(440.0) == 69

def test_freq_to_midi_c4():
    assert freq_to_midi(261.63) == 60

def test_freq_to_midi_silence():
    assert freq_to_midi(0) == -1

def test_estimate_freq_440hz():
    sr = 44100
    t = np.arange(sr // 10) / sr  # 100ms
    samples = np.sin(2 * np.pi * 440 * t)
    freq = estimate_freq(samples, sr)
    assert abs(freq - 440) < 10, f"Expected ~440Hz, got {freq}"

def test_estimate_freq_261hz():
    sr = 44100
    t = np.arange(sr // 10) / sr
    samples = np.sin(2 * np.pi * 261.63 * t)
    freq = estimate_freq(samples, sr)
    assert abs(freq - 261.63) < 10, f"Expected ~261Hz, got {freq}"

def test_estimate_freq_silence():
    samples = np.zeros(4410)
    assert estimate_freq(samples, 44100) == 0

def test_detect_key_c_major():
    midi = [60, 62, 64, 65, 67, 69, 71]
    key = detect_key(midi)
    assert "C" in key and "major" in key

def test_detect_key_empty():
    assert detect_key([]) == "unknown"

def test_analyze_intervals_steps():
    midi = [60, 62, 64, 65]
    result = analyze_intervals(midi)
    assert result["step (1-2)"] == 3

def test_analyze_intervals_single():
    assert analyze_intervals([60]) == {}

def test_suggest_role_bass():
    midi = [36, 38, 40]
    assert "bass" in suggest_role(midi, [100, 100, 100])

def test_suggest_role_melody():
    midi = [72, 74, 76, 72, 71]
    assert "melody" in suggest_role(midi, [100, 200, 150, 100, 300])

def test_suggest_role_empty():
    assert suggest_role([], []) == "silent"


# ---------------------------------------------------------------------------
# analyze_wav
# ---------------------------------------------------------------------------

def test_analyze_wav_empty_returns_message():
    """A WAV file with 0 frames returns the empty-audio message."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    # Write a valid header with 0 frames
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(44100)
        wf.writeframes(b"")
    try:
        result = analyze_wav(path)
        assert result == "Empty audio (0 samples)"
    finally:
        import os
        os.unlink(path)


def test_analyze_wav_sine_440hz_contains_note():
    """A 440 Hz sine wave should include A4 in the output."""
    samples = _sine_samples(440, duration_s=0.5)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    _write_wav(path, samples)
    try:
        result = analyze_wav(path)
        assert "A4" in result
        assert "440" in result or "A4" in result
    finally:
        import os
        os.unlink(path)


def test_analyze_wav_contains_duration_line():
    """Output always starts with a Duration / Peak / RMS summary line."""
    samples = _sine_samples(261, duration_s=0.3)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    _write_wav(path, samples)
    try:
        result = analyze_wav(path)
        assert result.startswith("Duration:")
        assert "Peak:" in result
        assert "RMS:" in result
    finally:
        import os
        os.unlink(path)


def test_analyze_wav_silent_shows_rests():
    """A silent WAV (all zeros) should show rest segments, no musical analysis."""
    samples = np.zeros(44100, dtype=np.int16)  # 1 second of silence
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    _write_wav(path, samples)
    try:
        result = analyze_wav(path)
        assert "rest" in result
        assert "Musical analysis:" not in result
    finally:
        import os
        os.unlink(path)


def test_analyze_wav_short_wav():
    """A very short WAV (< 100ms) still returns a valid string result."""
    samples = _sine_samples(440, duration_s=0.05)  # 50ms
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    _write_wav(path, samples)
    try:
        result = analyze_wav(path)
        assert isinstance(result, str)
        assert "Duration:" in result
    finally:
        import os
        os.unlink(path)


def test_analyze_wav_stereo_downmixed():
    """Stereo WAV is accepted and downmixed to mono without error."""
    mono = _sine_samples(440, duration_s=0.3)
    stereo = np.column_stack([mono, mono]).flatten().astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    _write_wav(path, stereo, n_channels=2)
    try:
        result = analyze_wav(path)
        assert isinstance(result, str)
        assert "A4" in result
    finally:
        import os
        os.unlink(path)


def test_analyze_wav_musical_analysis_section():
    """Sustained tone produces a Musical analysis section."""
    samples = _sine_samples(440, duration_s=1.0)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        path = f.name
    _write_wav(path, samples)
    try:
        result = analyze_wav(path)
        assert "Musical analysis:" in result
        assert "Key estimate:" in result
        assert "Pitch range:" in result
    finally:
        import os
        os.unlink(path)
