"""Tests for _audio module."""

import numpy as np
from pyxel_mcp._audio import (
    freq_to_note, freq_to_midi, estimate_freq,
    detect_key, analyze_intervals, suggest_role,
)

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
