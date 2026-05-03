"""Tests for judge_palette (Layer 2).

judge_palette is a pure function: takes an `read_palette` observation
plus a contract dict and returns a verdict dict.
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.palette import DEFAULT_CONTRACT, judge_palette


# Helper to build minimal observation dicts in the shape read_palette returns.
def _obs(score: int | None, n_warnings: int = 0) -> dict:
    hierarchy = None if score is None else {"score": score, "background": [], "environment": [], "interactive": []}
    contrast_warnings = [
        {"a": i, "b": i + 1, "ratio": 2.0, "message": ""}
        for i in range(n_warnings)
    ]
    return {
        "ok": True,
        "extended_palette": score is None,
        "hierarchy": hierarchy,
        "contrast_warnings": contrast_warnings,
        "errors": [],
    }


def test_pass_default_contract():
    """Score 2 + zero contrast warnings -> pass."""
    result = judge_palette(_obs(score=2, n_warnings=0))
    assert result["verdict"] == "pass"
    assert result["ok"] is True
    assert result["fail_route"] is None
    assert isinstance(result["evidence"], str) and result["evidence"]


def test_fail_low_hierarchy():
    """Score 0 -> fail (asset-planning route)."""
    result = judge_palette(_obs(score=0, n_warnings=0))
    assert result["verdict"] == "fail"
    assert result["ok"] is False
    assert result["fail_route"] == "asset-planning"


def test_fail_excess_contrast_warnings():
    """Score 2 but many warnings -> fail (sprite-quality route)."""
    result = judge_palette(_obs(score=2, n_warnings=10))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "sprite-quality"


def test_warn_intermediate_warnings():
    """Score 2, modest warnings (1 < n <= 5) -> warn."""
    result = judge_palette(_obs(score=2, n_warnings=3))
    assert result["verdict"] == "warn"
    assert result["ok"] is True  # warn is actionable, not blocking


def test_extended_palette_skipped():
    """hierarchy=None (extended palette) -> verdict 'pass' with skip reason."""
    obs = _obs(score=None, n_warnings=0)
    result = judge_palette(obs)
    # Extended palette can't be hierarchy-judged; treat as pass with note.
    assert result["verdict"] == "pass"
    assert "extended" in result["evidence"].lower() or "skipped" in result["evidence"].lower()


def test_contract_override_lower_threshold():
    """Custom min_hierarchy_score=1 lets score=1 pass."""
    contract = {"min_hierarchy_score": 1, "max_contrast_warnings": 1}
    result = judge_palette(_obs(score=1, n_warnings=0), contract=contract)
    assert result["verdict"] == "pass"


def test_default_contract_constants():
    """Document the default contract for downstream callers."""
    assert DEFAULT_CONTRACT["min_hierarchy_score"] == 2
    assert DEFAULT_CONTRACT["max_contrast_warnings"] == 1
