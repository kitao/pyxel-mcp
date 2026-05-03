"""Tests for judge_animation."""
from __future__ import annotations

from pyxel_mcp.judge._impl.animation import DEFAULT_CONTRACT, judge_animation


def _obs(*, diffs: list[float], palette_consistency: float = 1.0) -> dict:
    return {
        "ok": True,
        "image_index": 0,
        "regions": [],
        "palette_consistency": palette_consistency,
        "silhouette_stability": 1.0,
        "region_diffs": [
            {"from": i, "to": i + 1, "diff_ratio": d} for i, d in enumerate(diffs)
        ],
        "warnings": [],
        "errors": [],
    }


def test_pass_default():
    """All diffs in band + perfect palette consistency -> pass."""
    result = judge_animation(_obs(diffs=[0.10, 0.15, 0.12], palette_consistency=1.0))
    assert result["verdict"] == "pass"
    assert result["ok"] is True
    assert result["fail_route"] is None


def test_fail_diff_too_low():
    """diff_ratio below band -> 'no motion' fail."""
    result = judge_animation(_obs(diffs=[0.01], palette_consistency=1.0))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "sprite-quality"
    assert "diff" in result["evidence"].lower() or "motion" in result["evidence"].lower()


def test_fail_diff_too_high():
    """diff_ratio above band -> 'unrelated frames' fail."""
    result = judge_animation(_obs(diffs=[0.80], palette_consistency=1.0))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "sprite-quality"


def test_fail_palette_inconsistent():
    """Palette consistency well below threshold -> fail."""
    result = judge_animation(_obs(diffs=[0.20], palette_consistency=0.5))
    assert result["verdict"] == "fail"
    assert "palette" in result["evidence"].lower() or "consistency" in result["evidence"].lower()


def test_pass_with_one_extra_color_under_default():
    """5/6 consistency (one frame adds a colour, e.g. flame pulse) → pass.

    Pre-fix the default of 1.0 forced strict identity, banning any
    intentional palette tweak between paired frames. 0.83 (5/6) lets
    a single-color addition through while still rejecting wholesale
    palette swaps."""
    result = judge_animation(_obs(diffs=[0.20], palette_consistency=0.83))
    assert result["verdict"] == "pass"


def test_strict_consistency_via_contract_override():
    """An author who really wants strict identity can ask for it back."""
    result = judge_animation(
        _obs(diffs=[0.20], palette_consistency=0.83),
        contract={"min_palette_consistency": 1.0},
    )
    assert result["verdict"] == "fail"


def test_boundary_inclusive():
    """diff exactly on band edge -> pass."""
    result = judge_animation(_obs(diffs=[0.05, 0.50], palette_consistency=1.0))
    assert result["verdict"] == "pass"


def test_contract_override():
    """Looser band lets diffs through."""
    result = judge_animation(
        _obs(diffs=[0.80], palette_consistency=1.0),
        contract={"diff_band": [0.05, 0.95], "min_palette_consistency": 1.0},
    )
    assert result["verdict"] == "pass"


def test_empty_region_diffs():
    """No region_diffs (e.g., region_count=1 mistakenly) -> fail."""
    result = judge_animation(_obs(diffs=[], palette_consistency=1.0))
    assert result["verdict"] == "fail"


def test_default_contract_constants():
    """The 0.83 default for `min_palette_consistency` was lowered from
    1.0 in response to e2e validation: legitimate animation idioms
    (flame pulse, hit flash) introduce one extra colour in a single
    frame and would otherwise require an explicit override."""
    assert DEFAULT_CONTRACT["diff_band"] == [0.05, 0.50]
    assert DEFAULT_CONTRACT["min_palette_consistency"] == 0.83
