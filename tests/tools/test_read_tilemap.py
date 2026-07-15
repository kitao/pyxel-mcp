"""Tests for read_tilemap tool (spec §7.4)."""
import tempfile
from pathlib import Path

from pyxel_mcp.observe._harnesses.tools.read_tilemap import run as read_tilemap_run
from tests.conftest import SCRIPTS


def test_invalid_tilemap_index():
    """tilemap=999 is out of range — errors[0].phase == 'validation'."""
    result = read_tilemap_run({
        "script": str(SCRIPTS / "minimal.py"),
        "tilemap": 999,
    })
    assert result["errors"][0]["phase"] == "validation"
    assert result["tilemap_index"] == -1


def test_missing_script_validation():
    """Omitting script returns a validation phase error."""
    result = read_tilemap_run({"tilemap": 0})
    assert result["errors"][0]["phase"] == "validation"
    assert result["tilemap_index"] == -1


def test_missing_tilemap_validation():
    """Omitting tilemap returns a validation phase error."""
    result = read_tilemap_run({"script": str(SCRIPTS / "minimal.py")})
    assert result["errors"][0]["phase"] == "validation"


def test_round_trip_tilemap_demo():
    """tilemap_demo places 9 tiles at (5-7, 5-7) — verify usage and region."""
    result = read_tilemap_run({
        "script": str(SCRIPTS / "tilemap_demo.py"),
        "tilemap": 0,
    })
    assert result["errors"] == []
    assert result["tilemap_index"] == 0
    assert result["size"] == [256, 256]
    assert result["usage"].get("1,0", 0) == 9
    assert result["region"] == {"x": 5, "y": 5, "w": 3, "h": 3}
    assert result["zero_tile_used"] is True
    assert result["zero_tile_nonempty"] is False
    # Full 256x256 tilemap exceeds 4096 — tiles should be None
    assert result["tiles"] is None


def test_nonempty_zero_tile_is_reported():
    result = read_tilemap_run({
        "script": str(SCRIPTS / "tilemap_zero_zero_trap.py"),
        "tilemap": 0,
    })
    assert result["errors"] == []
    assert result["zero_tile_used"] is True
    assert result["zero_tile_nonempty"] is True


def test_render_to_png():
    """render_path produces a PNG file on disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        png_path = str(Path(tmpdir) / "tilemap0.png")
        result = read_tilemap_run({
            "script": str(SCRIPTS / "tilemap_demo.py"),
            "tilemap": 0,
            "render_path": png_path,
        })
        assert result["errors"] == []
        assert Path(result["rendered"]).resolve() == Path(png_path).resolve()
        assert Path(result["rendered"]).exists()
        assert Path(png_path).stat().st_size > 0


def test_render_path_must_be_absolute():
    result = read_tilemap_run({
        "script": str(SCRIPTS / "tilemap_demo.py"),
        "tilemap": 0,
        "render_path": "tilemap0.png",
    })
    assert result["errors"][0]["phase"] == "validation"
    assert "absolute" in result["errors"][0]["message"]
