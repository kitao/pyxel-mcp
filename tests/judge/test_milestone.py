"""Tests for judge_milestone (Pattern D).

Index `run()` snapshots by (kind, frame) and evaluate per-frame predicates
sourced from PLAN.md milestones.
"""
from __future__ import annotations

from pyxel_mcp.judge._impl.milestone import judge_milestone


def _state(frame: int, **values) -> dict:
    return {"frame": frame, "kind": "state", "values": dict(values)}


def _layout(frame: int, **fields) -> dict:
    return {"frame": frame, "kind": "layout", **fields}


def _run_result(snapshots: list[dict]) -> dict:
    return {
        "ok": True,
        "snapshots": snapshots,
        "assertions": [],
        "exit_status": "ok",
        "frame_count": 100,
        "elapsed_seconds": 1.0,
        "log": "",
        "seeded": False,
        "errors": [],
    }


def test_pass_single_predicate():
    """One assert at one frame, predicate True -> pass."""
    obs = _run_result([_state(10, scene="PLAY", score=0)])
    contract = {"asserts": [{"frame": 10, "predicate": "scene == 'PLAY'"}]}
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "pass"
    assert result["ok"] is True


def test_fail_predicate_false():
    """Predicate evaluates False -> fail (playthrough)."""
    obs = _run_result([_state(10, scene="MENU")])
    contract = {"asserts": [{"frame": 10, "predicate": "scene == 'PLAY'"}]}
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "playthrough"


def test_fail_no_snapshot_at_frame():
    """No state snapshot at requested frame -> fail (playthrough)."""
    obs = _run_result([_state(5, scene="PLAY")])
    contract = {"asserts": [{"frame": 10, "predicate": "scene == 'PLAY'"}]}
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "playthrough"


def test_fail_predicate_parse_error():
    """Invalid predicate syntax -> fail (spec)."""
    obs = _run_result([_state(10, scene="PLAY")])
    contract = {"asserts": [{"frame": 10, "predicate": "scene =="}]}
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "spec"


def test_fail_predicate_unknown_name():
    """Predicate references undefined name -> fail (spec)."""
    obs = _run_result([_state(10, scene="PLAY")])
    contract = {"asserts": [{"frame": 10, "predicate": "undefined_var > 0"}]}
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "spec"


def test_multi_assert_all_pass():
    """Multiple asserts all pass."""
    obs = _run_result([
        _state(10, scene="PLAY", score=0),
        _state(50, scene="PLAY", score=100),
        _state(99, scene="WIN"),
    ])
    contract = {
        "asserts": [
            {"frame": 10, "predicate": "scene == 'PLAY'"},
            {"frame": 50, "predicate": "score >= 100"},
            {"frame": 99, "predicate": "scene == 'WIN'"},
        ],
    }
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "pass"


def test_multi_assert_one_fails():
    """Multiple asserts, one fails -> overall fail."""
    obs = _run_result([
        _state(10, scene="PLAY"),
        _state(50, scene="PLAY", score=50),  # score not high enough
    ])
    contract = {
        "asserts": [
            {"frame": 10, "predicate": "scene == 'PLAY'"},
            {"frame": 50, "predicate": "score >= 100"},
        ],
    }
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "playthrough"


def test_dotted_attribute_access():
    """Dotted-path attr like 'player.x' should evaluate via nested namespace."""
    obs = _run_result([_state(10, **{"player.x": 50, "player.y": 100})])
    contract = {"asserts": [{"frame": 10, "predicate": "player.x > 10 and player.y < 200"}]}
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "pass"


def test_layout_kind_predicate():
    """Predicate evaluating against a layout snapshot."""
    obs = _run_result([_layout(20, h_balance=0.85, v_balance=0.7)])
    contract = {
        "asserts": [
            {"frame": 20, "kind": "layout", "predicate": "h_balance > 0.7"},
        ],
    }
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "pass"


def test_empty_asserts_passes():
    """No asserts to evaluate -> trivially pass."""
    obs = _run_result([])
    result = judge_milestone(obs, {"asserts": []})
    assert result["verdict"] == "pass"


def test_run_crashed_short_circuits():
    """If the run itself crashed, milestone judging fails immediately."""
    obs = _run_result([])
    obs["exit_status"] = "crashed"
    obs["errors"] = [{"phase": "game_loop", "message": "boom"}]
    obs["ok"] = False
    contract = {"asserts": [{"frame": 10, "predicate": "scene == 'PLAY'"}]}
    result = judge_milestone(obs, contract)
    assert result["verdict"] == "fail"
    assert result["fail_route"] == "playthrough"
