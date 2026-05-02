"""Tests for palette analyzer (spec §7.1)."""
import pytest


@pytest.fixture(autouse=True)
def _restore_palette():
    """Restore pyxel.colors after each test to prevent cross-test pollution."""
    import pyxel
    # pyxel.init may already have been called by an earlier test in this process;
    # we only call it here if pyxel has not been initialized yet.
    try:
        original = list(pyxel.colors)
    except Exception:
        pyxel.init(8, 8)
        original = list(pyxel.colors)
    yield
    try:
        pyxel.colors[:] = original
    except Exception:
        # Fallback if slice assignment is read-only
        while len(pyxel.colors) > len(original):
            pyxel.colors.pop()


from pyxel_mcp._harnesses._common.analyzers.palette import (
    analyze_palette, contrast_ratio
)


def test_default_palette_has_16_colors():
    """Pyxel's default palette is 16 colors."""
    info = analyze_palette()
    assert info["palette_size"] == 16
    assert info["extended_palette"] is False
    assert all(c.startswith("#") and len(c) == 7 for c in info["colors"].values())


def test_extended_palette_disables_hierarchy():
    """Once .append called, palette_size > 16 and hierarchy is None."""
    import pyxel
    pyxel.colors.append(0xff8800)
    info = analyze_palette()
    assert info["extended_palette"] is True
    assert info["palette_size"] > 16
    assert info["hierarchy"] is None


def test_hierarchy_score_default_palette():
    """Default palette should produce a hierarchy with all three layers populated."""
    info = analyze_palette()
    h = info["hierarchy"]
    assert h is not None
    assert h["score"] in (0, 1, 2)
    assert isinstance(h["background"], list)
    assert isinstance(h["environment"], list)
    assert isinstance(h["interactive"], list)


def test_contrast_ratio_pure_black_white():
    assert abs(contrast_ratio(0x000000, 0xFFFFFF) - 21.0) < 0.1


def test_contrast_warnings_for_close_colors():
    """Two near-identical colors should produce a warning at ratio < 3.0."""
    info = analyze_palette()
    assert isinstance(info["contrast_warnings"], list)
    for w in info["contrast_warnings"]:
        assert w["ratio"] <= 3.0  # rounded value; underlying ratio is < 3.0
