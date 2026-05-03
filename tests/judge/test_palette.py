"""Tests for judge_palette (Layer 2).

judge_palette is a pure function: takes a `read_palette` observation
plus a contract dict and returns a verdict dict with two sub-verdicts.
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.palette import DEFAULT_CONTRACT, judge_palette


def _obs(score: int | None, n_warnings: int = 0) -> dict:
    """Build a minimal observation in the shape read_palette returns."""
    hierarchy = (
        None if score is None
        else {"score": score, "background": [], "environment": [], "interactive": []}
    )
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


# ---------- happy path ---------------------------------------------------

def test_pass_default_contract():
    """Score 2 + zero contrast warnings -> pass on both sub-verdicts."""
    result = judge_palette(_obs(score=2, n_warnings=0))
    assert result["verdict"] == "pass"
    assert result["ok"] is True
    assert result["fail_route"] is None
    assert result["sub_verdicts"]["hierarchy"] == "pass"
    assert result["sub_verdicts"]["contrast"] == "pass"


# ---------- hierarchy sub-verdict ----------------------------------------

def test_hierarchy_fail_routes_to_asset_planning():
    """Score 0 -> hierarchy fail, asset-planning route."""
    result = judge_palette(_obs(score=0, n_warnings=0))
    assert result["sub_verdicts"]["hierarchy"] == "fail"
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "asset-planning"


def test_hierarchy_warn_just_below_threshold():
    """Score 1 (one below default min 2) → hierarchy warn."""
    result = judge_palette(_obs(score=1, n_warnings=0))
    assert result["sub_verdicts"]["hierarchy"] == "warn"
    assert result["sub_verdicts"]["contrast"] == "pass"
    assert result["verdict"] == "warn"


# ---------- contrast sub-verdict -----------------------------------------

def test_contrast_fail_routes_to_sprite_quality():
    """Many warnings (above pass+warn band) → contrast fail, sprite-quality route."""
    result = judge_palette(_obs(score=2, n_warnings=10))
    assert result["sub_verdicts"]["contrast"] == "fail"
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "sprite-quality"


def test_contrast_warn_within_band():
    """3-color-per-material rule produces ~9 warnings on a 3-material game.
    With the new default of 5, that's a warn (5 < 9 ≤ 5+_WARN_BAND=9)."""
    result = judge_palette(_obs(score=2, n_warnings=8))
    assert result["sub_verdicts"]["contrast"] == "warn"
    assert result["sub_verdicts"]["hierarchy"] == "pass"
    assert result["verdict"] == "warn"


def test_contrast_pass_under_default_for_3_warnings():
    """3 contrast warnings — well within the new default of 5 → pass."""
    result = judge_palette(_obs(score=2, n_warnings=3))
    assert result["sub_verdicts"]["contrast"] == "pass"
    assert result["verdict"] == "pass"


def test_contrast_warn_under_strict_override():
    """An override pulls the threshold back to 1; 3 warnings then warn."""
    result = judge_palette(
        _obs(score=2, n_warnings=3),
        contract={"max_contrast_warnings": 1},
    )
    assert result["sub_verdicts"]["contrast"] == "warn"


# ---------- combined behaviour -------------------------------------------

def test_overall_verdict_is_worst_of_two_sub_verdicts():
    """Hierarchy pass + contrast warn → overall warn."""
    result = judge_palette(_obs(score=2, n_warnings=8))
    assert result["sub_verdicts"]["hierarchy"] == "pass"
    assert result["sub_verdicts"]["contrast"] == "warn"
    assert result["verdict"] == "warn"


def test_hierarchy_fail_dominates_over_contrast_warn():
    """When both are non-pass, fail dominates warn."""
    result = judge_palette(_obs(score=0, n_warnings=8))
    assert result["sub_verdicts"]["hierarchy"] == "fail"
    assert result["sub_verdicts"]["contrast"] == "warn"
    assert result["verdict"] == "fail"
    # fail_route prefers the hierarchy fail
    assert result["fail_route"] == "asset-planning"


def test_contrast_fail_routes_when_hierarchy_passes():
    result = judge_palette(_obs(score=2, n_warnings=20))
    assert result["sub_verdicts"]["contrast"] == "fail"
    assert result["fail_route"] == "sprite-quality"


# ---------- extended palette ---------------------------------------------

def test_extended_palette_passes_hierarchy_check():
    """hierarchy=None (extended palette) -> hierarchy sub-verdict 'pass'
    with a skip reason; contrast still applies."""
    result = judge_palette(_obs(score=None, n_warnings=0))
    assert result["sub_verdicts"]["hierarchy"] == "pass"
    assert "extended" in result["evidence"].lower() or "skip" in result["evidence"].lower()
    assert result["details"]["extended_palette"] is True


# ---------- contract override --------------------------------------------

def test_contract_override_lowers_hierarchy_threshold():
    """Custom min_hierarchy_score=1 lets score=1 pass."""
    result = judge_palette(
        _obs(score=1, n_warnings=0),
        contract={"min_hierarchy_score": 1},
    )
    assert result["sub_verdicts"]["hierarchy"] == "pass"
    assert result["verdict"] == "pass"


# ---------- default constants --------------------------------------------

def test_default_contract_constants():
    """Document the v1.0.0 default contract.

    The 5 default for `max_contrast_warnings` was raised from 1 in
    response to an e2e validation finding: the skill's own
    3-color-per-material rule (shadow / base / highlight per material)
    inevitably produces 3 sibling-hue contrast warnings per material,
    so a 3-material game lands at 9-12 warnings naturally."""
    assert DEFAULT_CONTRACT["min_hierarchy_score"] == 2
    assert DEFAULT_CONTRACT["max_contrast_warnings"] == 5
