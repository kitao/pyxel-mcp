"""Tests for judge_genre.

Validate PLAN.md `## Genre Identity` rules against one or more run results.
Uses the same sandboxed predicate evaluator as judge_milestone, but the
namespace exposes run-aggregate signals (assertions, log, exit_status).
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.genre import judge_genre


def _run_result(*, assertions: list[dict] | None = None, log: str = "",
                exit_status: str = "ok", frame_count: int = 100) -> dict:
    return {
        "ok": exit_status in ("ok", "stalled"),
        "snapshots": [],
        "assertions": assertions or [],
        "exit_status": exit_status,
        "frame_count": frame_count,
        "elapsed_seconds": 1.0,
        "log": log,
        "seeded": False,
        "errors": [],
    }


def test_pass_simple_rule():
    """Single rule, predicate True -> pass."""
    obs = _run_result(assertions=[{"name": "L1_GRAVITY", "passed": True, "message": None}])
    contract = {"rules": [{"name": "L1: gravity works", "verify": "'L1_GRAVITY' in assertions_passed"}]}
    result = judge_genre(obs, contract)
    assert result["verdict"] == "pass"
    assert result["ok"] is True


def test_fail_rule_predicate_false():
    """Predicate False -> fail (playthrough)."""
    obs = _run_result(assertions=[{"name": "L1_GRAVITY", "passed": False, "message": None}])
    contract = {"rules": [{"name": "L1: gravity works", "verify": "'L1_GRAVITY' in assertions_passed"}]}
    result = judge_genre(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "playthrough"


def test_fail_no_rules():
    """No rules in contract -> fail (spec) — genre identity must be specified."""
    result = judge_genre(_run_result(), {"rules": []})
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "spec"


def test_fail_missing_rules_key():
    """Contract without 'rules' -> fail (spec)."""
    result = judge_genre(_run_result(), {})
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "spec"


def test_multi_rules_all_pass():
    obs = _run_result(
        assertions=[
            {"name": "L1_GRAVITY", "passed": True, "message": None},
            {"name": "L2_ENEMY", "passed": True, "message": None},
        ],
        log="WIN!\n",
    )
    contract = {
        "rules": [
            {"name": "L1: gravity", "verify": "'L1_GRAVITY' in assertions_passed"},
            {"name": "L2: enemy", "verify": "'L2_ENEMY' in assertions_passed"},
            {"name": "L3: clearable", "verify": "'WIN' in log"},
        ],
    }
    result = judge_genre(obs, contract)
    assert result["verdict"] == "pass"


def test_multi_rules_some_fail():
    obs = _run_result(
        assertions=[{"name": "L1_GRAVITY", "passed": True, "message": None}],
        log="",
    )
    contract = {
        "rules": [
            {"name": "L1", "verify": "'L1_GRAVITY' in assertions_passed"},
            {"name": "L3", "verify": "'WIN' in log"},
        ],
    }
    result = judge_genre(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "playthrough"
    # details.results should record per-rule outcomes
    rules = result["details"]["results"]
    assert any(r["name"] == "L1" and r["passed"] for r in rules)
    assert any(r["name"] == "L3" and not r["passed"] for r in rules)


def test_predicate_parse_error_routes_to_spec():
    obs = _run_result()
    contract = {"rules": [{"name": "broken", "verify": "in assertions_passed"}]}
    result = judge_genre(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "spec"


def test_namespace_exposes_frame_count_and_exit_status():
    obs = _run_result(frame_count=300, exit_status="ok")
    contract = {"rules": [
        {"name": "ran long enough", "verify": "frame_count >= 100 and exit_status == 'ok'"},
    ]}
    result = judge_genre(obs, contract)
    assert result["verdict"] == "pass"
