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


@pytest.fixture(autouse=True)
def _clear_image_banks():
    """Wipe all image banks back to transparent (palette index 0) after
    each test. Without this, a `pset` in one test leaks into the next:
    `test_hierarchy_score_*` would all see the union of every prior
    test's drawing operations.
    """
    import pyxel
    yield
    try:
        for img in pyxel.images:
            img.rect(0, 0, img.width, img.height, 0)
    except Exception:
        pass


from pyxel_mcp.observe._harnesses._common.analyzers.palette import (
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


def test_hierarchy_returns_three_layer_lists():
    """Hierarchy dict must always carry the three named layers as lists."""
    info = analyze_palette()
    h = info["hierarchy"]
    assert h is not None
    assert h["score"] in (0, 1, 2)
    assert isinstance(h["background"], list)
    assert isinstance(h["environment"], list)
    assert isinstance(h["interactive"], list)


def test_hierarchy_score_zero_when_no_image_content():
    """An empty image bank scores 0 — no layers have any drawn pixels.

    Pre-fix this scored 2 because the score was based on palette
    capacity rather than used indices: default-palette games passed the
    check vacuously even when the script drew nothing.
    """
    info = analyze_palette()
    assert info["used_indices"] == []
    assert info["hierarchy"]["score"] == 0


def test_hierarchy_score_grows_with_used_layers():
    """Drawing into one bg + one env + one interactive index → score 2."""
    import pyxel
    pyxel.images[0].pset(0, 0, 1)   # background layer (1 ∈ {0,1,5})
    pyxel.images[0].pset(0, 1, 3)   # environment layer (3 ∈ {3,4,13})
    pyxel.images[0].pset(0, 2, 8)   # interactive layer (8 ∈ {8,10,11})
    info = analyze_palette()
    assert info["hierarchy"]["score"] == 2
    assert info["hierarchy"]["background"] == [1]
    assert info["hierarchy"]["environment"] == [3]
    assert info["hierarchy"]["interactive"] == [8]


def test_hierarchy_score_one_when_only_two_layers_drawn():
    """Two layers drawn → score 1."""
    import pyxel
    pyxel.images[0].pset(2, 0, 5)   # bg
    pyxel.images[0].pset(2, 1, 13)  # env
    # No interactive pixel
    info = analyze_palette()
    assert info["hierarchy"]["score"] == 1


def test_hierarchy_score_zero_when_only_off_layer_indices_drawn():
    """Drawing colours that aren't in any of the three named layers → 0."""
    import pyxel
    # 7 (white), 12 (cyan-ish), 15 (peach) are not in the default
    # bg/env/interactive sets — none of the three layers gets a hit.
    pyxel.images[0].pset(3, 0, 7)
    pyxel.images[0].pset(3, 1, 12)
    pyxel.images[0].pset(3, 2, 15)
    info = analyze_palette()
    assert info["hierarchy"]["score"] == 0
    assert info["hierarchy"]["background"] == []
    assert info["hierarchy"]["environment"] == []
    assert info["hierarchy"]["interactive"] == []


def test_contrast_ratio_pure_black_white():
    assert abs(contrast_ratio(0x000000, 0xFFFFFF) - 21.0) < 0.1


def test_contrast_warnings_for_close_colors():
    """Stored ratio <= 3.0 (rounded from raw < 3.0 filter inside the analyzer)."""
    info = analyze_palette()
    assert isinstance(info["contrast_warnings"], list)
    for w in info["contrast_warnings"]:
        assert w["ratio"] <= 3.0  # rounded value; underlying ratio is < 3.0


def test_used_indices_field_present():
    """analyze_palette returns used_indices as a sorted list of int."""
    info = analyze_palette()
    assert "used_indices" in info
    assert isinstance(info["used_indices"], list)
    assert all(isinstance(i, int) for i in info["used_indices"])
    assert info["used_indices"] == sorted(info["used_indices"])


def test_contrast_warnings_filtered_to_used_indices():
    """When only a few indices appear in image banks, contrast_warnings must
    not reference unused indices."""
    import pyxel
    # Write a single 1x1 pixel of color 8 (red) into bank 0 (0,0). Other banks
    # are all-zero (default). Index 0 is excluded by convention; index 8 is
    # the only used non-zero index → no pairs → no warnings.
    pyxel.images[0].pset(0, 0, 8)
    try:
        info = analyze_palette()
        assert info["used_indices"] == [8], (
            f"expected used={{8}}, got {info['used_indices']}"
        )
        assert info["contrast_warnings"] == [], (
            f"expected no warnings with single used index, got "
            f"{len(info['contrast_warnings'])}"
        )
    finally:
        pyxel.images[0].pset(0, 0, 0)


def test_contrast_warnings_only_among_used_pairs():
    """With two used indices, at most one pair can be flagged — never pairs
    that include an unused index."""
    import pyxel
    pyxel.images[0].pset(0, 0, 8)   # red
    pyxel.images[0].pset(1, 0, 14)  # pink (close to red)
    try:
        info = analyze_palette()
        assert sorted(info["used_indices"]) == [8, 14]
        # All warnings must reference only indices in {8, 14}.
        for w in info["contrast_warnings"]:
            assert w["a"] in (8, 14) and w["b"] in (8, 14), (
                f"warning references unused index: {w}"
            )
        # The total warning count is <= C(2, 2) = 1.
        assert len(info["contrast_warnings"]) <= 1
    finally:
        pyxel.images[0].pset(0, 0, 0)
        pyxel.images[0].pset(1, 0, 0)


def test_contrast_warnings_uses_co_located_not_just_used():
    """Two used indices that never appear adjacent in pixel data must not
    produce a contrast warning — spec §7.1's "commonly co-located indices"."""
    import pyxel
    pyxel.images[0].pset(0, 0, 8)    # red
    pyxel.images[0].pset(10, 10, 14)  # pink, far away from the red pixel
    try:
        info = analyze_palette()
        assert sorted(info["used_indices"]) == [8, 14]
        assert info["co_located_pairs"] == [], (
            f"unexpected co-located pairs: {info['co_located_pairs']}"
        )
        assert info["contrast_warnings"] == [], (
            f"non-adjacent indices were flagged: {info['contrast_warnings']}"
        )
    finally:
        pyxel.images[0].pset(0, 0, 0)
        pyxel.images[0].pset(10, 10, 0)


def test_co_located_pairs_field_is_sorted_tuples():
    """co_located_pairs is a sorted list of (i, j) with i < j."""
    import pyxel
    # Place a 1x2 swatch of (3, 11) — adjacent vertically.
    pyxel.images[0].pset(5, 5, 3)
    pyxel.images[0].pset(5, 6, 11)
    try:
        info = analyze_palette()
        pairs = info["co_located_pairs"]
        assert (3, 11) in pairs or [3, 11] in pairs, (
            f"expected (3, 11) in pairs, got {pairs}"
        )
        for p in pairs:
            assert p[0] < p[1], f"pair not sorted ascending: {p}"
    finally:
        pyxel.images[0].pset(5, 5, 0)
        pyxel.images[0].pset(5, 6, 0)


# --- performance regression guard --------------------------------------------


def test_scan_image_banks_completes_under_500ms():
    """Full 3-bank scan (3 * 65k px) must complete fast post-vectorization.

    Pre-fix this took multiple seconds via nested pget loops; post-fix it's
    numpy operations on contiguous buffers (~5-30ms range expected).
    """
    import time
    import pyxel
    # Splatter some pixels across bank 0 to ensure the unique/pair paths run.
    for i in range(100):
        pyxel.images[0].pset(i % 64, i // 64, (i % 15) + 1)
    try:
        from pyxel_mcp.observe._harnesses._common.analyzers.palette import _scan_image_banks
        t0 = time.monotonic()
        used, pairs = _scan_image_banks()
        elapsed = time.monotonic() - t0
        assert elapsed < 0.5, (
            f"_scan_image_banks took {elapsed*1000:.1f}ms (limit 500ms)"
        )
        assert isinstance(used, set)
        assert isinstance(pairs, set)
    finally:
        pyxel.images[0].cls(0)
