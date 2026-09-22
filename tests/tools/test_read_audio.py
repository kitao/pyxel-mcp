"""Tests for read_audio tool."""

import wave

import numpy as np
import pytest

from tests.conftest import SCRIPTS


def read_audio_run(payload: dict) -> dict:
    from pyxel_mcp.dispatch import dispatch

    # Match production isolation: Pyxel's native synthesizer keeps DSP state
    # across saves even when another script reinitializes its sound banks.
    return dispatch("read_audio", payload)


def test_render_sound_to_wav(tmp_path):
    out = tmp_path / "snd.wav"
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "sound_demo.py"),
            "target": {"sound": 0},
            "output_path": str(out),
        }
    )
    assert out.exists()
    assert result["sample_rate"] == 22050
    assert result["channels"] == 1
    assert result["duration_seconds"] > 0
    assert len(result["notes"]) >= 3  # c3, e3, g3


def test_render_target_validation():
    # Both keys: validation error
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "sound_demo.py"),
            "target": {"sound": 0, "music": 0},
            "output_path": "/tmp/x.wav",
        }
    )
    assert result["errors"][0]["phase"] == "validation"


def test_output_path_must_be_absolute():
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "sound_demo.py"),
            "target": {"sound": 0},
            "output_path": "sound.wav",
        }
    )
    assert result["errors"][0]["phase"] == "validation"
    assert "absolute" in result["errors"][0]["message"]


def test_render_empty_slot_warns():
    """Rendering an empty slot returns success with peak=0 and warning."""
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "minimal.py"),
            "target": {"sound": 1},
            "output_path": "/tmp/x.wav",
        }
    )
    assert result["peak_amplitude"] == 0.0
    assert any(
        "empty" in w.lower() or "not populated" in w.lower() for w in result["warnings"]
    )


def test_render_music_to_wav(tmp_path):
    """Music slot wraps a sound; render path uses audio_obj.save with the
    music slot index. Verifies the `else: music` branch in read_audio.run.
    """
    out = tmp_path / "music.wav"
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "music_demo.py"),
            "target": {"music": 0},
            "output_path": str(out),
        }
    )
    assert out.exists()
    assert result["errors"] == []
    assert result["sample_rate"] == 22050
    assert result["duration_seconds"] > 0


def test_render_empty_music_slot_warns():
    """An unpopulated music slot returns success with warning."""
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "minimal.py"),
            "target": {"music": 1},
            "output_path": "/tmp/empty_music.wav",
        }
    )
    assert any(
        "empty" in w.lower() or "not populated" in w.lower() for w in result["warnings"]
    )


def test_render_target_missing_keys():
    """target with neither sound nor music key is a validation error."""
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "sound_demo.py"),
            "target": {},
            "output_path": "/tmp/x.wav",
        }
    )
    assert result["errors"][0]["phase"] == "validation"


def test_render_music_out_of_range():
    """music slot index >= len(pyxel.musics) is a validation error."""
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "music_demo.py"),
            "target": {"music": 9999},
            "output_path": "/tmp/x.wav",
        }
    )
    assert result["errors"][0]["phase"] == "validation"
    assert "out of range" in result["errors"][0]["message"]


def test_music_target_warns_about_fixed_window(tmp_path):
    """Music renders always use a fixed 10-second window; a populated slot
    must warn so agents know audio beyond 10 seconds is truncated.
    """
    result = read_audio_run(
        {
            "script": str(SCRIPTS / "music_demo.py"),
            "target": {"music": 0},
            "output_path": str(tmp_path / "music.wav"),
        }
    )
    assert result["ok"] is True
    assert any("10-second window" in w for w in result["warnings"])


def _sound_script(tmp_path, setup):
    script = tmp_path / "sound.py"
    script.write_text(
        "import pyxel\npyxel.init(8, 8)\n"
        + setup
        + "\npyxel.run(lambda: None, lambda: None)\n"
    )
    return str(script)


def _wav_peak(path):
    with wave.open(path, "rb") as audio:
        samples = np.frombuffer(audio.readframes(audio.getnframes()), dtype="<i2")
    return np.abs(samples.astype(np.int32)).max() / 32768


def test_tracker_fields_repeat_independently(tmp_path):
    script = _sound_script(
        tmp_path, "pyxel.sounds[0].set('c3d3e3f3g3', 'tp', '17', 'nhq', 5)"
    )
    result = read_audio_run(
        {
            "script": script,
            "target": {"sound": 0},
            "output_path": str(tmp_path / "s.wav"),
        }
    )
    assert result["ok"]
    assert [note["tone"] for note in result["notes"]] == ["t", "p", "t", "p", "t"]
    assert [note["volume"] for note in result["notes"]] == [1, 7, 1, 7, 1]
    assert [note["effect"] for note in result["notes"]] == ["n", "h", "q", "n", "h"]


@pytest.mark.parametrize("mode", ["mml", "pcm"])
def test_non_tracker_audio_reports_measured_peak(tmp_path, mode):
    if mode == "mml":
        setup = "pyxel.sounds[0].mml('T120 @1 O4 L4 C')"
    else:
        source = tmp_path / "source.wav"
        with wave.open(str(source), "wb") as audio:
            audio.setparams((1, 2, 22050, 0, "NONE", "not compressed"))
            audio.writeframes(np.full(2205, 8192, dtype="<i2").tobytes())
        setup = f"pyxel.sounds[0].pcm({str(source)!r})"
    script = _sound_script(tmp_path, setup)
    result = read_audio_run(
        {
            "script": script,
            "target": {"sound": 0},
            "output_path": str(tmp_path / "s.wav"),
        }
    )
    assert result["ok"]
    assert result["peak_amplitude"] == pytest.approx(_wav_peak(result["path"]))
    assert result["peak_amplitude"] > 0
    assert not any("empty" in warning for warning in result["warnings"])


def test_infinite_mml_renders_a_bounded_window(tmp_path):
    script = _sound_script(tmp_path, "pyxel.sounds[0].mml('T120 @1 O4 L4 [C]')")
    result = read_audio_run(
        {
            "script": script,
            "target": {"sound": 0},
            "output_path": str(tmp_path / "s.wav"),
        }
    )
    assert result["ok"]
    assert result["duration_seconds"] == pytest.approx(10.0)
    assert result["peak_amplitude"] > 0
    assert any("loops indefinitely" in warning for warning in result["warnings"])
