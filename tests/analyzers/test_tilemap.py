"""Tests for tilemap analyzer (spec §7.4)."""
import pytest
import pyxel


# Initialize pyxel once for this module (second call panics in Pyxel 2.9.4).
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


from pyxel_mcp._harnesses._common.analyzers.tilemap import analyze_tilemap


def test_basic_tilemap_usage():
    pyxel.images[0].pset(8, 0, 11)
    for ty in range(5, 8):
        for tx in range(5, 8):
            pyxel.tilemaps[0].pset(tx, ty, (1, 0))
    result = analyze_tilemap(tilemap=0)
    # 9 tiles of (1,0) placed
    assert result["usage"].get("1,0", 0) == 9
    assert result["bounding_box"] == {"x": 5, "y": 5, "w": 3, "h": 3}
    assert result["trap_warning"] is False


def test_zero_zero_trap_detected():
    pyxel.images[0].pset(0, 0, 11)  # source (0,0) has visible content
    result = analyze_tilemap(tilemap=0)
    assert result["trap_warning"] is True


def test_large_tilemap_returns_none_tiles():
    # Pyxel default tilemap size is 256x256 = 65536 cells, well above 4096.
    result = analyze_tilemap(tilemap=0)
    assert result["tiles"] is None


def test_invalid_index_via_tool():
    """inspect_tilemap should report validation phase for invalid index."""
    from pyxel_mcp._harnesses.tools.inspect_tilemap import run as tool_run
    from tests.conftest import SCRIPTS
    result = tool_run({"script": str(SCRIPTS / "minimal.py"), "tilemap": 999})
    assert result["errors"][0]["phase"] == "validation"
