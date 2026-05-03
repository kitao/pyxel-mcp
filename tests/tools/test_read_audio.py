"""Tests for read_audio tool (spec §8.3)."""
import pytest
from tests.conftest import SCRIPTS


def read_audio_run(payload: dict) -> dict:
    from pyxel_mcp.observe._harnesses.tools.read_audio import run
    return run(payload)


def test_render_sound_to_wav(tmp_path):
    out = tmp_path / "snd.wav"
    result = read_audio_run({
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
    result = read_audio_run({
        "script": str(SCRIPTS / "sound_demo.py"),
        "target": {"sound": 0, "music": 0},
        "output_path": "/tmp/x.wav",
    })
    assert result["errors"][0]["phase"] == "validation"


def test_render_empty_slot_warns():
    """Rendering an empty slot returns success with peak=0 and warning."""
    result = read_audio_run({
        "script": str(SCRIPTS / "minimal.py"),
        "target": {"sound": 1},
        "output_path": "/tmp/x.wav",
    })
    assert result["peak_amplitude"] == 0.0
    assert any("empty" in w.lower() or "not populated" in w.lower() for w in result["warnings"])


def test_render_music_to_wav(tmp_path):
    """Music slot wraps a sound; render path uses audio_obj.save with the
    music slot index. Verifies the `else: music` branch in read_audio.run.
    """
    out = tmp_path / "music.wav"
    result = read_audio_run({
        "script": str(SCRIPTS / "music_demo.py"),
        "target": {"music": 0},
        "output_path": str(out),
    })
    assert out.exists()
    assert result["errors"] == []
    assert result["sample_rate"] == 22050
    assert result["duration_seconds"] > 0


def test_render_empty_music_slot_warns():
    """An unpopulated music slot returns success with warning."""
    result = read_audio_run({
        "script": str(SCRIPTS / "minimal.py"),
        "target": {"music": 1},
        "output_path": "/tmp/empty_music.wav",
    })
    assert any("empty" in w.lower() or "not populated" in w.lower() for w in result["warnings"])


def test_render_target_missing_keys():
    """target with neither sound nor music key is a validation error."""
    result = read_audio_run({
        "script": str(SCRIPTS / "sound_demo.py"),
        "target": {},
        "output_path": "/tmp/x.wav",
    })
    assert result["errors"][0]["phase"] == "validation"


def test_render_music_out_of_range():
    """music slot index >= len(pyxel.musics) is a validation error."""
    result = read_audio_run({
        "script": str(SCRIPTS / "music_demo.py"),
        "target": {"music": 9999},
        "output_path": "/tmp/x.wav",
    })
    assert result["errors"][0]["phase"] == "validation"
    assert "out of range" in result["errors"][0]["message"]
