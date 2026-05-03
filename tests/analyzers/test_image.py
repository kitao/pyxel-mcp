"""Tests for image bank analyzer (spec §7.2)."""
import pytest
import pyxel


# Initialize pyxel once for this module (second call panics in Pyxel 2.9.4).
def _ensure_pyxel():
    try:
        _ = pyxel.images[0].width
    except Exception:
        pyxel.init(64, 64)


_ensure_pyxel()


@pytest.fixture(autouse=True)
def _clear_image_bank():
    """Clear image bank 0 before and after each test to prevent cross-test pollution."""
    pyxel.images[0].cls(0)
    yield
    pyxel.images[0].cls(0)


from pyxel_mcp.observe._harnesses._common.analyzers.image import analyze_image


def test_full_bank_pixels_none_when_large():
    """A 256x256 bank has 65536 pixels — pixels should be None."""
    result = analyze_image(image=0, x=0, y=0, w=None, h=None)
    assert result["pixels"] is None
    assert result["bank_size"] == [256, 256]
    assert "color_count" in result


def test_small_region_includes_pixels():
    """An 8x8 region has 64 pixels — pixels should be included."""
    pyxel.images[0].pset(0, 0, 11)
    pyxel.images[0].pset(7, 7, 11)
    result = analyze_image(image=0, x=0, y=0, w=8, h=8)
    assert result["pixels"] is not None
    assert len(result["pixels"]) == 8
    assert result["pixels"][0][0] == 11
    assert result["pixels"][7][7] == 11


def test_oversize_region_clamped_with_warning():
    """Region beyond bank bounds is clamped."""
    result = analyze_image(image=0, x=200, y=200, w=100, h=100)
    # Bank is 256x256. (200..300, 200..300) clamps to (200..256, 200..256) = 56x56.
    assert result["region"] == {"x": 200, "y": 200, "w": 56, "h": 56}
    assert any("clamp" in w.lower() for w in result["warnings"])


def test_symmetry_and_edge_density_only_for_small_regions():
    """For region <= 4096 px, symmetry and edge_density are computed; otherwise None."""
    small = analyze_image(image=0, x=0, y=0, w=8, h=8)
    assert small["symmetry"] is not None
    large = analyze_image(image=0, x=0, y=0, w=None, h=None)
    assert large["symmetry"] is None
    assert large["edge_density"] is None


# --- verdict field tests (Task 2A) -------------------------------------------


def test_verdict_full_bank_scan_returns_none():
    """A full 256x256 bank scan has pixels=None — verdict must be null since
    fill_ratio over 65k pixels is meaningless as a sprite metric."""
    result = analyze_image(image=0, x=0, y=0, w=None, h=None)
    assert result["pixels"] is None
    assert result["verdict"] is None


def test_verdict_pass_well_filled_three_color_sprite():
    """Sprite with 3+ colors and fill in [0.15, 0.95] → pass."""
    # 8x8 region: ~50% non-zero with 3 distinct non-zero colors (8, 11, 14).
    for x in range(8):
        for y in range(8):
            if (x + y) % 2 == 0:
                pyxel.images[0].pset(x, y, [8, 11, 14][(x + y) % 3])
    result = analyze_image(image=0, x=0, y=0, w=8, h=8)
    assert result["verdict"] == "pass", (
        f"expected pass; fill={result['fill_ratio']}, "
        f"colors={list(result['color_count'].keys())}"
    )


def test_verdict_fail_when_only_one_color():
    """Single non-zero color sprite → fail (insufficient color depth)."""
    pyxel.images[0].pset(0, 0, 8)
    pyxel.images[0].pset(1, 0, 8)
    pyxel.images[0].pset(2, 0, 8)
    result = analyze_image(image=0, x=0, y=0, w=8, h=8)
    # 3 non-zero pixels out of 64 → fill ~0.047 (< 0.15) AND only 2 entries
    # (color 0 background + color 8). Since color_count includes color 0,
    # len == 2 — but fill is way below 0.15 by more than 0.05, so → fail.
    assert result["fill_ratio"] < 0.10
    assert result["verdict"] == "fail"


def test_verdict_warn_for_two_color_well_filled():
    """Fill in band but only 2 color_count entries (1 bg + 1 fg) → warn."""
    # 8x8: fill ~50% of cells with color 8 only.
    for x in range(8):
        for y in range(4):
            pyxel.images[0].pset(x, y, 8)
    result = analyze_image(image=0, x=0, y=0, w=8, h=8)
    # color_count: {0: 32, 8: 32} → len == 2; fill_ratio == 0.5 (in band).
    assert len(result["color_count"]) == 2
    assert 0.15 <= result["fill_ratio"] <= 0.95
    assert result["verdict"] == "warn"


def test_verdict_warn_at_lower_fill_boundary():
    """fill_ratio just below 0.15 (within 0.05) with 3 colors → warn."""
    from pyxel_mcp.observe._harnesses._common.analyzers.image import _image_verdict
    # boundary: fill 0.12 (dist = 0.03 from 0.15); 3 colors
    assert _image_verdict([[0]], 0.12, {0: 56, 1: 4, 2: 4}) == "warn"


def test_verdict_fail_at_far_below_lower_fill():
    """fill_ratio more than 0.05 below 0.15 → fail."""
    from pyxel_mcp.observe._harnesses._common.analyzers.image import _image_verdict
    # 0.05 below threshold = 0.10 still within 0.05; 0.09 is just outside
    assert _image_verdict([[0]], 0.05, {0: 60, 1: 2, 2: 2}) == "fail"


# --- performance regression guard --------------------------------------------


def test_analyze_image_full_bank_under_500ms():
    """Full-bank scan (256x256 = 65k px) must complete fast post-vectorization.

    Pre-fix: nested pget loops; post-fix: numpy slice on data_ptr().
    """
    import time
    t0 = time.monotonic()
    result = analyze_image(image=0, x=0, y=0, w=None, h=None)
    elapsed = time.monotonic() - t0
    assert elapsed < 0.5, (
        f"analyze_image full-bank took {elapsed*1000:.1f}ms (limit 500ms)"
    )
    assert result["bank_size"] == [256, 256]
