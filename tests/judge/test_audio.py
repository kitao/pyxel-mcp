"""Tests for judge_audio.

Validates a read_audio observation against an audio manifest entry.
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.audio import DEFAULT_CONTRACT, judge_audio


def _obs(*, peak: float, n_notes: int, warnings: list[str] | None = None) -> dict:
    return {
        "ok": True,
        "path": "/tmp/test.wav",
        "duration_seconds": 0.5,
        "sample_rate": 22050,
        "channels": 1,
        "peak_amplitude": peak,
        "notes": [{"frame": i, "note": "C3", "tone": "s", "volume": 5, "effect": "n"}
                  for i in range(n_notes)],
        "warnings": warnings or [],
        "errors": [],
    }


def test_pass_default():
    """Loud + populated -> pass."""
    result = judge_audio(_obs(peak=0.5, n_notes=8))
    assert result["verdict"] == "pass"
    assert result["ok"] is True
    assert result["fail_route"] is None


def test_fail_empty_slot():
    """peak=0 + 0 notes + empty warning -> sprite-quality fail."""
    result = judge_audio(_obs(peak=0.0, n_notes=0, warnings=["sound slot 1 is empty / not populated"]))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "sprite-quality"
    assert "empty" in result["evidence"].lower()


def test_fail_quiet_audio():
    """Has notes but peak below threshold -> scaffolding fail (volumes too low)."""
    result = judge_audio(_obs(peak=0.001, n_notes=8))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "scaffolding"
    assert "peak" in result["evidence"].lower()


def test_fail_too_few_notes():
    """Loud but no notes (e.g., constant tone, sample-only) -> scaffolding fail."""
    result = judge_audio(_obs(peak=0.5, n_notes=0))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "scaffolding"


def test_boundary_inclusive():
    """peak exactly at threshold and exactly min_notes -> pass (inclusive)."""
    result = judge_audio(_obs(peak=0.02, n_notes=1))
    assert result["verdict"] == "pass"


def test_contract_override():
    """Custom higher threshold makes a previously-passing observation fail."""
    result = judge_audio(_obs(peak=0.05, n_notes=4),
                         contract={"min_peak": 0.10, "min_notes": 1})
    assert result["verdict"] == "fail"


def test_default_contract_constants():
    assert DEFAULT_CONTRACT["min_peak"] == 0.02
    assert DEFAULT_CONTRACT["min_notes"] == 1
