"""Tests for render_audio tool (spec §8.3)."""
import pytest
from tests.conftest import SCRIPTS


def render_audio_run(payload: dict) -> dict:
    from pyxel_mcp._harnesses.tools.render_audio import run
    return run(payload)


def test_render_sound_to_wav(tmp_path):
    out = tmp_path / "snd.wav"
    result = render_audio_run({
        "script": str(SCRIPTS / "sound_demo.py"),
        "target": {"sound": 0},
        "output_path": str(out),
    })
    assert out.exists()
    assert result["sample_rate"] == 22050
    assert result["channels"] == 1
    assert result["duration_seconds"] > 0
    assert len(result["notes"]) >= 3  # c3, e3, g3


def test_render_target_validation():
    # Both keys: validation error
    result = render_audio_run({
        "script": str(SCRIPTS / "sound_demo.py"),
        "target": {"sound": 0, "music": 0},
        "output_path": "/tmp/x.wav",
    })
    assert result["errors"][0]["phase"] == "validation"


def test_render_empty_slot_warns():
    """Rendering an empty slot returns success with peak=0 and warning."""
    result = render_audio_run({
        "script": str(SCRIPTS / "minimal.py"),
        "target": {"sound": 1},
        "output_path": "/tmp/x.wav",
    })
    assert result["peak_amplitude"] == 0.0
    assert any("empty" in w.lower() or "not populated" in w.lower() for w in result["warnings"])
