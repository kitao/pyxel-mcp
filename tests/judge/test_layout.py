"""Tests for judge_layout.

Validates a run() result containing at least one layout snapshot against
contract thresholds for h_balance and quadrant density.
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.layout import DEFAULT_CONTRACT, judge_layout


def _layout_snap(*, frame: int = 0, h_balance: float = 1.0, v_balance: float = 1.0,
                 quadrants: tuple[float, float, float, float] = (0.25, 0.25, 0.25, 0.25)) -> dict:
    return {
        "frame": frame, "kind": "layout",
        "h_balance": h_balance, "v_balance": v_balance,
        "quadrant_density": list(quadrants),
        "center_of_mass": [80.0, 64.0],
        "text_positions": [],
        "warnings": [],
    }


def _run_result(*layout_snaps: dict) -> dict:
    return {
        "ok": True,
        "snapshots": list(layout_snaps),
        "assertions": [],
        "exit_status": "ok",
        "frame_count": 100,
        "elapsed_seconds": 1.0,
        "log": "",
        "seeded": False,
        "errors": [],
    }


def test_pass_balanced_layout():
    result = judge_layout(_run_result(_layout_snap(h_balance=0.85)))
    assert result["verdict"] == "pass"
    assert result["ok"] is True


def test_fail_h_balance_low():
    result = judge_layout(_run_result(_layout_snap(h_balance=0.4)))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "scaffolding"
    assert "h_balance" in result["evidence"] or "balance" in result["evidence"].lower()


def test_fail_empty_quadrant():
    """One quadrant with zero density -> fail."""
    result = judge_layout(_run_result(_layout_snap(quadrants=(0.5, 0.5, 0.0, 0.0))))
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "scaffolding"
    assert "quadrant" in result["evidence"].lower()


def test_fail_no_layout_snapshot():
    """run result with no layout snapshots -> fail."""
    result = judge_layout(_run_result())
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "scaffolding"


def test_boundary_h_balance():
    """h_balance exactly at min -> pass."""
    result = judge_layout(_run_result(_layout_snap(h_balance=0.70)))
    assert result["verdict"] == "pass"


def test_contract_override_lower_threshold():
    result = judge_layout(
        _run_result(_layout_snap(h_balance=0.4)),
        contract={"min_h_balance": 0.3, "min_quadrant_density": 0.0001},
    )
    assert result["verdict"] == "pass"


def test_evaluates_first_layout_snapshot():
    """If multiple layout snapshots exist, first is evaluated."""
    snaps = _run_result(
        _layout_snap(frame=10, h_balance=0.85),
        _layout_snap(frame=50, h_balance=0.4),
    )
    result = judge_layout(snaps)
    assert result["verdict"] == "pass"
    assert result["details"]["evaluated_frame"] == 10


def test_default_contract_constants():
    assert DEFAULT_CONTRACT["min_h_balance"] == 0.70
    assert DEFAULT_CONTRACT["min_quadrant_density"] == 0.0001
