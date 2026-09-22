"""Tests for tilemap analyzer."""

import pytest
import pyxel


# Initialize pyxel once for this module (a second call panics).
def _ensure_pyxel():
    try:
        _ = pyxel.tilemaps[0].width
    except Exception:
        pyxel.init(64, 64)


_ensure_pyxel()


@pytest.fixture(autouse=True)
def _reset_state():
    """Reset image bank 0 and tilemap 0 before each test."""
    pyxel.images[0].cls(0)
    pyxel.tilemaps[0].cls((0, 0))
    yield
    pyxel.images[0].cls(0)
    pyxel.tilemaps[0].cls((0, 0))


from pyxel_mcp.observe._harnesses._common.analyzers.tilemap import analyze_tilemap


def test_basic_tilemap_usage():
    pyxel.images[0].pset(8, 0, 11)
    for ty in range(5, 8):
        for tx in range(5, 8):
            pyxel.tilemaps[0].pset(tx, ty, (1, 0))
    result = analyze_tilemap(tilemap=0)
    # 9 tiles of (1,0) placed
    assert result["usage"].get("1,0", 0) == 9
    assert result["region"] == {"x": 5, "y": 5, "w": 3, "h": 3}
    assert result["zero_tile_used"] is True
    assert result["zero_tile_nonempty"] is False


def test_zero_tile_facts_are_reported_separately():
    pyxel.images[0].pset(0, 0, 11)  # source (0,0) has visible content
    result = analyze_tilemap(tilemap=0)
    assert result["zero_tile_used"] is True
    assert result["zero_tile_nonempty"] is True


def test_imgsrc_resolved_when_tilemap_image_assigned(tmp_path):
    """Image wrappers for the same bank still resolve to that bank's pixels."""
    from PIL import Image

    tm = pyxel.tilemaps[0]
    tm.imgsrc = pyxel.images[1]
    pyxel.images[1].cls(7)
    try:
        out = tmp_path / "bank-source.png"
        result = analyze_tilemap(tilemap=0, render_path=str(out))
        assert result["imgsrc"] == 1
        assert result["zero_tile_nonempty"] is True
        assert result["errors"] == []
        with Image.open(out) as image:
            assert image.getpixel((0, 0)) == tuple(pyxel.colors[7].to_bytes(3, "big"))
    finally:
        tm.imgsrc = 0
        pyxel.images[1].cls(0)


def test_standalone_image_source_and_partial_edge_tile(tmp_path):
    from PIL import Image

    source = pyxel.Image(10, 10)
    source.cls(7)
    tm = pyxel.tilemaps[0]
    tm.imgsrc = source
    tm.pset(0, 0, (1, 1))
    try:
        out = tmp_path / "custom-source.png"
        result = analyze_tilemap(tilemap=0, render_path=str(out))
        assert result["imgsrc"] is None
        assert result["zero_tile_nonempty"] is True
        with Image.open(out) as image:
            assert image.getpixel((1, 1)) == tuple(pyxel.colors[7].to_bytes(3, "big"))
            assert image.getpixel((2, 2)) == tuple(pyxel.colors[0].to_bytes(3, "big"))
    finally:
        tm.imgsrc = 0


def test_large_tilemap_returns_none_tiles():
    # Pyxel default tilemap size is 256x256 = 65536 cells, well above 4096.
    result = analyze_tilemap(tilemap=0)
    assert result["tiles"] is None


def test_invalid_index_via_tool():
    """read_tilemap should report validation phase for invalid index."""
    from pyxel_mcp.observe._harnesses.tools.read_tilemap import run as tool_run
    from tests.conftest import SCRIPTS

    result = tool_run({"script": str(SCRIPTS / "minimal.py"), "tilemap": 999})
    assert result["errors"][0]["phase"] == "validation"


# --- performance regression guard --------------------------------------------


def test_analyze_tilemap_full_scan_under_500ms():
    """Full 256x256 = 65k cell scan must complete fast post-vectorization.

    Pre-fix: nested pget loops over 65k cells; post-fix: numpy ops on
    data_ptr() snapshots.
    """
    import time

    # Place some content so usage/bbox paths run.
    for tx in range(32):
        for ty in range(32):
            pyxel.tilemaps[0].pset(tx, ty, (tx % 8, ty % 8))
    try:
        t0 = time.monotonic()
        result = analyze_tilemap(tilemap=0)
        elapsed = time.monotonic() - t0
        assert elapsed < 0.5, (
            f"analyze_tilemap full scan took {elapsed * 1000:.1f}ms (limit 500ms)"
        )
        assert result["region"] is not None
    finally:
        pyxel.tilemaps[0].cls((0, 0))
