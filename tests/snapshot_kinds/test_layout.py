"""Tests for snapshot_kinds.layout (spec §6.4.4)."""
from pyxel_mcp.observe._harnesses._common.pyxel_patcher import headless_pyxel
from pyxel_mcp.observe._harnesses._common.snapshot_kinds.layout import capture


def test_uniform_screen_high_balance():
    """A solid color fills both halves; h_balance and v_balance should be ~1.0."""
    import pyxel
    with headless_pyxel():
        pyxel.init(32, 32)
        pyxel.cls(7)
        result = capture({"frame": 0, "kind": "layout"})
    assert result["h_balance"] >= 0.95
    assert result["v_balance"] >= 0.95


def test_left_only_low_h_balance():
    """A blob only on the left half should make h_balance significantly less than 1."""
    import pyxel
    with headless_pyxel():
        pyxel.init(32, 32)
        pyxel.cls(0)
        pyxel.rect(0, 0, 16, 32, 11)  # left half filled
        result = capture({"frame": 0, "kind": "layout"})
    assert result["h_balance"] < 0.5


def test_quadrant_densities_sum_to_one():
    import pyxel
    with headless_pyxel():
        pyxel.init(32, 32)
        # Use cls to fill entire screen regardless of actual screen dimensions
        # (headless_pyxel skips re-init when width > 0, so screen may be larger)
        pyxel.cls(11)
        result = capture({"frame": 0, "kind": "layout"})
    densities = result["quadrant_density"]
    assert len(densities) == 4
    # All quadrants equally filled → each ~0.25
    for d in densities:
        assert 0.2 <= d <= 0.3


def test_center_of_mass_for_centered_blob():
    import pyxel
    with headless_pyxel():
        pyxel.init(32, 32)
        pyxel.cls(0)
        pyxel.rect(14, 14, 4, 4, 11)
        result = capture({"frame": 0, "kind": "layout"})
    cx, cy = result["center_of_mass"]
    assert 14 <= cx <= 18
    assert 14 <= cy <= 18


def test_layout_result_exposes_only_implemented_metrics():
    import pyxel
    with headless_pyxel():
        pyxel.init(32, 32)
        pyxel.cls(0)
        result = capture({"frame": 0, "kind": "layout"})
    assert "text_positions" not in result


# --- performance regression guard --------------------------------------------


def test_layout_capture_under_500ms_for_256x256_screen():
    """Full layout analysis on a 256x256 screen must complete fast.

    Pre-fix: nested pget loops over 65k pixels; post-fix: one np.frombuffer
    + reshape on screen.data_ptr().
    """
    import time
    import pyxel
    with headless_pyxel():
        pyxel.init(256, 256)
        pyxel.cls(7)
        pyxel.rect(10, 10, 64, 64, 11)
        t0 = time.monotonic()
        result = capture({"frame": 0, "kind": "layout"})
        elapsed = time.monotonic() - t0
    assert elapsed < 0.5, (
        f"layout capture took {elapsed*1000:.1f}ms (limit 500ms)"
    )
    assert result["h_balance"] is not None
