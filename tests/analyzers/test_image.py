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
