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


# --- verdict field tests (Task 2A) -------------------------------------------


def test_verdict_pass_for_default_palette_no_pixels():
    """Default palette + no co-located pairs → score 2 + 0 warnings → pass."""
    info = analyze_palette()
    # Default: hierarchy.score == 2 (all 3 layers in default 16-color palette);
    # no image content means no co-located pairs and 0 contrast_warnings.
    assert info["hierarchy"]["score"] == 2
    assert len(info["contrast_warnings"]) == 0
    assert info["verdict"] == "pass"


def test_verdict_extended_palette_returns_none():
    """Extended palette skips hierarchy analysis, so verdict is None."""
    import pyxel
    pyxel.colors.append(0x123456)
    info = analyze_palette()
    assert info["extended_palette"] is True
    assert info["hierarchy"] is None
    assert info["verdict"] is None


def test_verdict_pass_with_one_warning():
    """score 2 + 1 warning is still pass (boundary)."""
    from pyxel_mcp._harnesses._common.analyzers.palette import _palette_verdict
    h = {"score": 2, "background": [0], "environment": [3], "interactive": [8]}
    assert _palette_verdict(h, [{"a": 1, "b": 2, "ratio": 1.5, "message": "x"}]) == "pass"


def test_verdict_warn_when_two_to_five_warnings():
    """score 2 + 2 warnings → warn; score 2 + 5 warnings → warn (upper boundary)."""
    from pyxel_mcp._harnesses._common.analyzers.palette import _palette_verdict
    h = {"score": 2, "background": [0], "environment": [3], "interactive": [8]}
    two = [{"a": i, "b": i + 1, "ratio": 1.0, "message": ""} for i in range(2)]
    five = [{"a": i, "b": i + 1, "ratio": 1.0, "message": ""} for i in range(5)]
    assert _palette_verdict(h, two) == "warn"
    assert _palette_verdict(h, five) == "warn"


def test_verdict_fail_on_low_hierarchy():
    """Hierarchy score 0 or 1 → fail regardless of warning count."""
    from pyxel_mcp._harnesses._common.analyzers.palette import _palette_verdict
    h0 = {"score": 0, "background": [], "environment": [], "interactive": []}
    h1 = {"score": 1, "background": [0], "environment": [3], "interactive": []}
    assert _palette_verdict(h0, []) == "fail"
    assert _palette_verdict(h1, []) == "fail"


def test_verdict_fail_when_more_than_five_warnings():
    """score 2 but more than 5 warnings → fail (boundary above warn band)."""
    from pyxel_mcp._harnesses._common.analyzers.palette import _palette_verdict
    h = {"score": 2, "background": [0], "environment": [3], "interactive": [8]}
    six = [{"a": i, "b": i + 1, "ratio": 1.0, "message": ""} for i in range(6)]
    assert _palette_verdict(h, six) == "fail"


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
        from pyxel_mcp._harnesses._common.analyzers.palette import _scan_image_banks
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
