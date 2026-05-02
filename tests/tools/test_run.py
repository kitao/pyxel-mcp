"""Tests for run() — dynamic execution driver (spec §6)."""
from pyxel_mcp._harnesses.tools.run import run as run_tool
from tests.conftest import SCRIPTS


def test_minimal_script_completes():
    result = run_tool({"script": str(SCRIPTS / "minimal.py"), "frames": 3})
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 3
    assert result["errors"] == []


def test_random_seed_seeds():
    result = run_tool({"script": str(SCRIPTS / "minimal.py"), "frames": 1, "random_seed": 42})
    assert result["seeded"] is True


def test_random_seed_default_is_unseeded():
    result = run_tool({"script": str(SCRIPTS / "minimal.py"), "frames": 1})
    assert result["seeded"] is False


def test_frames_zero_is_validation_error():
    result = run_tool({"script": str(SCRIPTS / "minimal.py"), "frames": 0})
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_init_crash_reports_script_import():
    result = run_tool({"script": str(SCRIPTS / "crashing_init.py"), "frames": 1})
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "script_import"


def test_update_crash_reports_game_loop_with_frame():
    result = run_tool({"script": str(SCRIPTS / "crashing_update.py"), "frames": 30})
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "game_loop"
    assert result["errors"][0]["frame"] == 5
    assert result["frame_count"] == 5


def test_missing_asset_reports_asset_load():
    result = run_tool({"script": str(SCRIPTS / "missing_asset.py"), "frames": 1})
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "asset_load"


def test_no_pyxel_run_reports_script_import():
    """Script that calls pyxel.init but never pyxel.run should crash via
    RunNotCalledError → script_import phase."""
    result = run_tool({"script": str(SCRIPTS / "no_pyxel_run.py"), "frames": 1})
    assert result["exit_status"] == "crashed"
    assert result["errors"][0]["phase"] == "script_import"


def test_no_main_guard_script_runs():
    """Script that instantiates App() at top level (no `__main__` guard) should
    still load and complete normally."""
    result = run_tool({"script": str(SCRIPTS / "no_main_guard.py"), "frames": 2})
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 2


def test_crash_at_first_frame():
    """update() raising on the very first call must report frame=0,
    frame_count=0, exit_status=crashed."""
    result = run_tool({"script": str(SCRIPTS / "crashing_first_frame.py"), "frames": 5})
    assert result["exit_status"] == "crashed"
    assert result["frame_count"] == 0
    assert result["errors"][0]["phase"] == "game_loop"
    assert result["errors"][0]["frame"] == 0


def test_negative_random_seed_is_validation_error():
    """random_seed must be non-negative int."""
    result = run_tool({"script": str(SCRIPTS / "minimal.py"), "frames": 1, "random_seed": -1})
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_timeout_default_is_10():
    """Default timeout should be 10 (informational only — enforcement is at server)."""
    result = run_tool({"script": str(SCRIPTS / "minimal.py"), "frames": 1})
    assert result["exit_status"] == "ok"


def test_timeout_must_be_positive():
    result = run_tool({"script": str(SCRIPTS / "minimal.py"), "frames": 1, "timeout": 0})
    assert result["exit_status"] == "invalid"
    assert "timeout" in result["errors"][0]["message"].lower()
