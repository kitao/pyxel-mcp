"""Tests for judge_sprite.

Validates an `inspect_image` observation against a sprite manifest entry:
distinct colors and silhouette fill_ratio.
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.sprite import DEFAULT_CONTRACT, judge_sprite


def _obs(*, colors: int, fill: float) -> dict:
    return {
        "ok": True,
        "image_index": 0,
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
    """fill exactly at lower bound -> pass (inclusive)."""
    result = judge_sprite(_obs(colors=3, fill=0.15))
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
