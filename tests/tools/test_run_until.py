"""run(until=...) behavior tests."""
from tests.conftest import SCRIPTS
from pyxel_mcp.observe._harnesses.tools.run import run as run_tool

STATEFUL = str(SCRIPTS / "stateful_app.py")
LATE = str(SCRIPTS / "late_attr.py")
MINIMAL = str(SCRIPTS / "minimal.py")


def test_until_stops_at_condition_frame():
    result = run_tool({"script": STATEFUL, "frames": 100, "until": "counter >= 3"})
    assert result["ok"] is True
    assert result["until_met"] is True
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 3


def test_until_unmet_runs_to_frame_cap():
    result = run_tool({"script": STATEFUL, "frames": 5, "until": "counter >= 999"})
    assert result["ok"] is True
    assert result["until_met"] is False
    assert result["frame_count"] == 5


def test_until_absent_reports_null():
    result = run_tool({"script": MINIMAL, "frames": 2})
    assert result["until_met"] is None


def test_until_dotted_path():
    result = run_tool({"script": STATEFUL, "frames": 5, "until": "player.x >= 10"})
    assert result["until_met"] is True
    assert result["frame_count"] == 1


def test_until_late_attribute_warns_then_matches():
    result = run_tool({"script": LATE, "frames": 10, "until": "goal_reached"})
    assert result["until_met"] is True
    assert result["frame_count"] == 3
    assert "not yet satisfied" in result["log"]


def test_until_syntax_error_is_invalid():
    result = run_tool({"script": MINIMAL, "frames": 2, "until": "score >="})
    assert result["ok"] is False
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_until_empty_string_is_invalid():
    result = run_tool({"script": MINIMAL, "frames": 2, "until": "  "})
    assert result["ok"] is False
    assert result["exit_status"] == "invalid"


def test_until_runtime_error_crashes_with_until_phase():
    result = run_tool({"script": STATEFUL, "frames": 3, "until": "len(counter) > 0"})
    assert result["ok"] is False
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "until"


def test_until_with_inputs_stops_before_later_rows():
    result = run_tool({
        "script": STATEFUL, "frames": 50,
        "inputs": [{"frame": 40, "buttons": ["KEY_SPACE"]}],
        "until": "counter >= 2",
    })
    assert result["until_met"] is True
    assert result["frame_count"] == 2


def test_until_with_stall_window_no_interference():
    result = run_tool({
        "script": STATEFUL, "frames": 6, "until": "counter >= 999",
        "stall_window_frames": 3,
        "snapshots": [{"kind": "state", "frames": [0, 1, 2, 3, 4, 5], "attrs": ["counter"]}],
    })
    assert result["until_met"] is False
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 6
