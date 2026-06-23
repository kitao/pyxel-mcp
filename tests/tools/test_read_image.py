"""Tests for read_image tool (spec §7.2)."""
import tempfile
from pathlib import Path

from pyxel_mcp.observe._harnesses.tools.read_image import run as read_image_run
from tests.conftest import SCRIPTS


def test_invalid_bank_index():
    """image=999 is out of range — errors[0].phase == 'validation'."""
    result = read_image_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 999,
    })
    assert result["errors"][0]["phase"] == "validation"
    assert result["image_index"] == -1


def test_round_trip_default_region():
    """Valid script + image=0 returns 256x256 bank with no errors."""
    result = read_image_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
    })
    assert result["errors"] == []
    assert result["bank_size"] == [256, 256]
    assert result["image_index"] == 0
    assert result["region"] == {"x": 0, "y": 0, "w": 256, "h": 256}
    # Full bank (65536 px) exceeds threshold — pixels should be None
    assert result["pixels"] is None
    assert "color_count" in result
    assert "fill_ratio" in result


def test_render_to_png():
    """render_path produces a PNG file on disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        png_path = str(Path(tmpdir) / "bank0.png")
        result = read_image_run({
            "script": str(SCRIPTS / "palette_default.py"),
            "image": 0,
            "x": 0, "y": 0, "w": 8, "h": 8,
            "render_path": png_path,
        })
        assert result["errors"] == []
        # Compare resolved paths because macOS /var → /private/var symlink
        assert Path(result["rendered"]).resolve() == Path(png_path).resolve()
        assert Path(result["rendered"]).exists()
        assert Path(png_path).stat().st_size > 0


def test_render_path_must_be_absolute():
    result = read_image_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
        "render_path": "bank0.png",
    })
    assert result["errors"][0]["phase"] == "validation"
    assert "absolute" in result["errors"][0]["message"]


def test_render_path_rejects_unexpanded_home():
    result = read_image_run({
        "script": str(SCRIPTS / "palette_default.py"),
        "image": 0,
        "render_path": "~/bank0.png",
    })
    assert result["errors"][0]["phase"] == "validation"
    assert "absolute" in result["errors"][0]["message"]
