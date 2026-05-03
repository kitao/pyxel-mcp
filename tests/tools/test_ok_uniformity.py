"""Verify the `ok: bool` field is uniformly present across all 9 tool responses.

The 0.11.0 redesign promises that `if not result["ok"]: handle(result["errors"])`
is a single uniform predicate across the whole tool surface. This file pins
that contract — both for success paths (ok=True) and validation/error paths
(ok=False).
"""
from pathlib import Path

from pyxel_mcp.observe._harnesses.tools.diff_frames import run as diff_frames_run
from pyxel_mcp.observe._harnesses.tools.read_animation import run as read_animation_run
from pyxel_mcp.observe._harnesses.tools.read_image import run as read_image_run
from pyxel_mcp.observe._harnesses.tools.read_palette import run as read_palette_run
from pyxel_mcp.observe._harnesses.tools.read_tilemap import run as read_tilemap_run
from pyxel_mcp.observe._harnesses.tools.pyxel_info import run as pyxel_info_run
from pyxel_mcp.observe._harnesses.tools.read_audio import run as read_audio_run
from pyxel_mcp.observe._harnesses.tools.run import run as run_run
from pyxel_mcp.observe._harnesses.tools.validate import run as validate_run
from tests.conftest import IMAGES, SCRIPTS


def test_run_ok_true_on_success():
    result = run_run({"script": str(SCRIPTS / "minimal.py"), "frames": 3})
    assert result["ok"] is True
    assert result["errors"] == []


def test_run_ok_false_on_invalid_payload():
    result = run_run({"script": str(SCRIPTS / "minimal.py"), "frames": 0})
    assert result["ok"] is False
    assert result["errors"][0]["phase"] == "validation"


def test_run_ok_false_on_crash():
    result = run_run({"script": str(SCRIPTS / "crashing_init.py"), "frames": 1})
    assert result["ok"] is False
    assert result["exit_status"] == "crashed"


def test_validate_ok_true_on_clean_script():
    result = validate_run({"script": str(SCRIPTS / "minimal.py")})
    assert result["ok"] is True


def test_validate_ok_false_on_missing_script():
    result = validate_run({"script": "/does/not/exist.py"})
    assert result["ok"] is False


def test_pyxel_info_ok_true():
    result = pyxel_info_run({})
    assert result["ok"] is True


def test_read_palette_ok_true():
    result = read_palette_run({"script": str(SCRIPTS / "palette_default.py")})
    assert result["ok"] is True


def test_read_palette_ok_false_on_missing_script():
    result = read_palette_run({"script": "/does/not/exist.py"})
    assert result["ok"] is False


def test_read_image_ok_true():
    result = read_image_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
    })
    assert result["ok"] is True


def test_read_image_ok_false_on_invalid_index():
    result = read_image_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 999,
    })
    assert result["ok"] is False


def test_read_animation_ok_true():
    result = read_animation_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
        "x": 0, "y": 0, "w": 8, "h": 8,
        "region_count": 3,
    })
    assert result["ok"] is True


def test_read_animation_ok_false_on_overflow():
    result = read_animation_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
        "x": 250, "y": 0, "w": 8, "h": 8,
        "region_count": 4,
    })
    assert result["ok"] is False


def test_read_tilemap_ok_true():
    result = read_tilemap_run({
        "script": str(SCRIPTS / "tilemap_demo.py"),
        "tilemap": 0,
    })
    assert result["ok"] is True


def test_read_tilemap_ok_false_on_invalid_index():
    result = read_tilemap_run({
        "script": str(SCRIPTS / "minimal.py"),
        "tilemap": 999,
    })
    assert result["ok"] is False


def test_read_audio_ok_true(tmp_path):
    result = read_audio_run({
        "script": str(SCRIPTS / "sound_demo.py"),
        "target": {"sound": 0},
        "output_path": str(tmp_path / "snd.wav"),
    })
    assert result["ok"] is True


def test_read_audio_ok_false_on_missing_target():
    result = read_audio_run({
        "script": str(SCRIPTS / "sound_demo.py"),
        "target": {},
        "output_path": "/tmp/x.wav",
    })
    assert result["ok"] is False


def test_diff_frames_ok_true_on_identical():
    result = diff_frames_run({
        "frame_a": str(IMAGES / "reference_a.png"),
        "frame_b": str(IMAGES / "reference_a.png"),
    })
    # Identical PNGs — comparison ran successfully (size_match True).
    assert result["ok"] is True
    assert result["identical"] is True


def test_diff_frames_ok_true_on_size_mismatch():
    """Size mismatch is informational, not an error — ok stays True."""
    result = diff_frames_run({
        "frame_a": str(IMAGES / "reference_a.png"),
        "frame_b": str(IMAGES / "reference_c_16x16.png"),
    })
    assert result["ok"] is True
    assert result["size_match"] is False


def test_diff_frames_ok_false_on_missing_input():
    result = diff_frames_run({
        "frame_a": "/nonexistent/a.png",
        "frame_b": str(IMAGES / "reference_a.png"),
    })
    assert result["ok"] is False
