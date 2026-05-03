"""Tests for judge_sprite.

Validates an `read_image` observation against a sprite manifest entry:
distinct colors and silhouette fill_ratio.
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.sprite import DEFAULT_CONTRACT, judge_sprite


def _obs(*, colors: int, fill: float, w: int = 16, h: int = 16) -> dict:
    return {
        "ok": True,
        "image_index": 0,
        "region": {"x": 0, "y": 0, "w": w, "h": h},
        "color_count": {i: 1 for i in range(colors)},
        "fill_ratio": fill,
        "warnings": [],
        "errors": [],
    }


def test_pass_default():
    """5 distinct colors + mid-band fill -> pass."""
    result = judge_sprite(_obs(colors=5, fill=0.5))
    assert result["verdict"] == "pass"
    assert result["ok"] is True
    assert result["fail_route"] is None


def test_fail_too_few_colors():
    """1 color is below min_distinct_colors=3."""
    result = judge_sprite(_obs(colors=1, fill=0.5))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "sprite-quality"
    assert "color" in result["evidence"].lower()


def test_fail_fill_too_low():
    """fill_ratio below silhouette band."""
    result = judge_sprite(_obs(colors=5, fill=0.05))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "sprite-quality"


def test_fail_fill_too_high():
    """fill_ratio above silhouette band."""
    result = judge_sprite(_obs(colors=5, fill=0.99))
    assert result["verdict"] == "fail"


def test_boundary_inclusive():
    """fill exactly at lower silhouette bound -> pass (inclusive).

    Tests the fill-ratio boundary, so use an 8×8 region (area-derived
    min=3) and supply 3 colours so the colour check isn't the gating
    factor."""
    result = judge_sprite(_obs(colors=3, fill=0.15, w=8, h=8))
    assert result["verdict"] == "pass"


def test_contract_override():
    """Custom min_distinct_colors=2 lets 2 colors pass."""
    result = judge_sprite(
        _obs(colors=2, fill=0.5),
        contract={"min_distinct_colors": 2, "silhouette": [0.15, 0.95]},
    )
    assert result["verdict"] == "pass"


def test_default_contract_constants():
    assert DEFAULT_CONTRACT["min_distinct_colors"] == 3
    assert DEFAULT_CONTRACT["silhouette"] == [0.15, 0.95]


# ---------- area-scaled default (P1-1) ------------------------------------

def test_4x4_sprite_passes_with_2_colors_by_default():
    """16-pixel sprites get a 2-colour floor — outline + body is enough.
    The e2e validation hit this exactly: a 4×4 ball with 2 colours had
    to use a contract override to pass under the old flat-3 default."""
    result = judge_sprite(_obs(colors=2, fill=0.5, w=4, h=4))
    assert result["verdict"] == "pass"
    assert result["details"]["min_distinct_colors"] == 2


def test_4x4_sprite_with_1_color_still_fails():
    result = judge_sprite(_obs(colors=1, fill=0.5, w=4, h=4))
    assert result["verdict"] == "fail"


def test_8x8_sprite_requires_3_colors():
    """Mid-size sprites have room for outline + body + shading."""
    result = judge_sprite(_obs(colors=3, fill=0.5, w=8, h=8))
    assert result["verdict"] == "pass"
    assert result["details"]["min_distinct_colors"] == 3


def test_8x8_sprite_with_2_colors_fails_against_area_default():
    result = judge_sprite(_obs(colors=2, fill=0.5, w=8, h=8))
    assert result["verdict"] == "fail"


def test_16x16_sprite_requires_4_colors_by_default():
    """16×16 has room for a real palette — bump the floor to 4."""
    result = judge_sprite(_obs(colors=4, fill=0.5, w=16, h=16))
    assert result["verdict"] == "pass"
    assert result["details"]["min_distinct_colors"] == 4


def test_16x16_sprite_with_3_colors_fails_against_area_default():
    result = judge_sprite(_obs(colors=3, fill=0.5, w=16, h=16))
    assert result["verdict"] == "fail"


def test_explicit_contract_min_overrides_area_default():
    """An explicit `min_distinct_colors` in the contract always wins —
    that's how a designer who really wants a 2-tone 16×16 sprite tells
    the gate to allow it."""
    result = judge_sprite(
        _obs(colors=2, fill=0.5, w=16, h=16),
        contract={"min_distinct_colors": 2},
    )
    assert result["verdict"] == "pass"
    assert result["details"]["min_distinct_colors"] == 2


def test_observation_with_no_region_falls_back_to_default():
    """If the observation has no region (synthetic test input), fall back
    to the documented DEFAULT_CONTRACT floor."""
    obs = {"color_count": {0: 1, 1: 1, 2: 1}, "fill_ratio": 0.5}
    result = judge_sprite(obs)
    assert result["details"]["min_distinct_colors"] == 3
    assert result["verdict"] == "pass"
