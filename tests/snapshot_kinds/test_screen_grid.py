"""Tests for snapshot_kinds.screen_grid (spec §6.4.2)."""
from pyxel_mcp._harnesses._common.pyxel_patcher import headless_pyxel
from pyxel_mcp._harnesses._common.snapshot_kinds.screen_grid import capture


def test_full_screen_capture():
    import pyxel
    with headless_pyxel():
        pyxel.init(8, 8)
        pyxel.cls(7)
        result = capture({"frame": 0, "kind": "screen_grid"})
    sw, sh = pyxel.width, pyxel.height
    assert result["bbox"] == [0, 0, sw, sh]
    assert len(result["grid"]) == sh
    assert all(len(row) == sw for row in result["grid"])
    assert all(cell == 7 for row in result["grid"] for cell in row)


def test_bbox_crop():
    import pyxel
    with headless_pyxel():
        pyxel.init(16, 16)
        pyxel.cls(0)
        pyxel.rect(2, 4, 4, 2, 11)  # 4x2 region of color 11
        result = capture({"frame": 0, "kind": "screen_grid", "bbox": [2, 4, 4, 2]})
    assert result["bbox"] == [2, 4, 4, 2]
    assert len(result["grid"]) == 2
    assert len(result["grid"][0]) == 4
    assert all(cell == 11 for row in result["grid"] for cell in row)


def test_bbox_clamping_with_warning():
    """bbox extending past screen edges is clamped with a warning."""
    import pyxel
    with headless_pyxel():
        pyxel.init(8, 8)
        result = capture({"frame": 0, "kind": "screen_grid", "bbox": [4, 4, 99, 99]})
    sw, sh = pyxel.width, pyxel.height
    assert result["bbox"] == [4, 4, sw - 4, sh - 4]  # clamped to fit
    assert any("clamp" in w.lower() for w in result.get("warnings", []))
