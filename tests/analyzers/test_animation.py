"""Tests for animation strip analyzer (spec §7.3)."""
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
def _restore_image_bank():
    """Clear image bank 0 before and after each test to prevent cross-test pollution."""
    pyxel.images[0].cls(0)
    yield
    pyxel.images[0].cls(0)


from pyxel_mcp._harnesses._common.analyzers.animation import analyze_animation


def test_two_identical_frames_high_stability():
    """Identical frames → palette_consistency 1.0, silhouette_stability 1.0."""
    pyxel.images[0].pset(0, 0, 11)
    pyxel.images[0].pset(8, 0, 11)  # same single pixel at the next region's origin
    result = analyze_animation(image=0, x=0, y=0, w=8, h=8, region_count=2, direction="horizontal")
    assert result["palette_consistency"] == pytest.approx(1.0)
    assert result["silhouette_stability"] == pytest.approx(1.0)


def test_two_distinct_frames_partial_stability():
    """Frames differing in one pixel produce stability < 1."""
    pyxel.images[0].pset(0, 0, 11)
    pyxel.images[0].pset(8, 0, 11)
    pyxel.images[0].pset(9, 0, 11)  # second region has 2 pixels
    result = analyze_animation(image=0, x=0, y=0, w=8, h=8, region_count=2, direction="horizontal")
    assert result["silhouette_stability"] < 1.0


def test_empty_pair_jaccard_returns_1():
    """Both regions fully empty → silhouette_stability defined as 1.0."""
    result = analyze_animation(image=0, x=0, y=0, w=8, h=8, region_count=2, direction="horizontal")
    assert result["silhouette_stability"] == pytest.approx(1.0)


def test_region_diffs_length_equals_regions_minus_one():
    result = analyze_animation(image=0, x=0, y=0, w=8, h=8, region_count=4, direction="horizontal")
    assert len(result["region_diffs"]) == 3  # consecutive pairs
    for d in result["region_diffs"]:
        assert "from" in d and "to" in d and "diff_ratio" in d


def test_vertical_direction():
    result = analyze_animation(image=0, x=0, y=0, w=8, h=8, region_count=2, direction="vertical")
    assert len(result["regions"]) == 2
    assert result["regions"][0]["region"]["y"] == 0
    assert result["regions"][1]["region"]["y"] == 8


def test_overflow_raises_validation_via_caller():
    """Caller's tool wrapper translates the overflow into a validation phase error;
    the analyzer itself raises ValueError on overflow."""
    with pytest.raises(ValueError, match="overflow"):
        analyze_animation(image=0, x=250, y=0, w=8, h=8, region_count=4, direction="horizontal")


# --- performance regression guard --------------------------------------------


def test_analyze_animation_under_500ms_for_8_frames():
    """8-frame strip analysis must complete fast post-vectorization."""
    import time
    t0 = time.monotonic()
    result = analyze_animation(
        image=0, x=0, y=0, w=16, h=16, region_count=8, direction="horizontal",
    )
    elapsed = time.monotonic() - t0
    assert elapsed < 0.5, (
        f"analyze_animation 8-frame took {elapsed*1000:.1f}ms (limit 500ms)"
    )
    assert len(result["region_diffs"]) == 7
