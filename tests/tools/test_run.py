"""Tests for run() — dynamic execution driver (spec §6)."""
import pytest
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


def test_log_captures_print_output():
    result = run_tool({"script": str(SCRIPTS / "printing.py"), "frames": 3})
    assert "init message" in result["log"]
    assert "update at frame 0" in result["log"]
    assert "update at frame 2" in result["log"]


def test_log_empty_when_no_print():
    """Script that never prints must produce an empty log string."""
    result = run_tool({"script": str(SCRIPTS / "minimal.py"), "frames": 3})
    assert result["log"] == ""


def test_log_includes_stderr():
    """Script that writes to sys.stderr must have that text in log."""
    result = run_tool({"script": str(SCRIPTS / "stderr_printing.py"), "frames": 1})
    assert "stderr message" in result["log"]


# --- Inputs ---

def _mouse_simulation_supported() -> bool:
    """Check whether Pyxel exposes either set_mouse_pos or mutable mouse_x/y."""
    import pyxel
    if hasattr(pyxel, "set_mouse_pos"):
        return True
    try:
        pyxel.mouse_x = 0  # type: ignore[attr-defined]
        return True
    except (AttributeError, TypeError):
        return False


def test_inputs_drive_state():
    result = run_tool({
        "script": str(SCRIPTS / "btn_responder.py"),
        "frames": 10,
        "inputs": [{"frame": 0, "buttons": ["KEY_RIGHT"]}],
        "snapshots": [{"frame": 9, "kind": "state", "attrs": ["x"]}],
    })
    # Right held for 10 frames → x should be 10 (one increment per update)
    assert result["exit_status"] == "ok"
    assert result["errors"] == []
    assert result["snapshots"][0]["values"]["x"] == 10


def test_btnp_only_on_press_edge():
    result = run_tool({
        "script": str(SCRIPTS / "btnp_responder.py"),
        "frames": 20,
        "inputs": [
            {"frame": 0, "buttons": ["KEY_SPACE"]},
            {"frame": 3, "buttons": []},
            {"frame": 6, "buttons": ["KEY_SPACE"]},
            {"frame": 10, "buttons": []},
        ],
        "snapshots": [{"frame": 19, "kind": "state", "attrs": ["jumps"]}],
    })
    # Two press edges → jumps == 2
    assert result["exit_status"] == "ok"
    assert result["errors"] == []
    assert result["snapshots"][0]["values"]["jumps"] == 2


def test_input_release_stops_movement():
    result = run_tool({
        "script": str(SCRIPTS / "btn_responder.py"),
        "frames": 10,
        "inputs": [
            {"frame": 0, "buttons": ["KEY_RIGHT"]},
            {"frame": 5, "buttons": []},
        ],
        "snapshots": [{"frame": 9, "kind": "state", "attrs": ["x"]}],
    })
    # x should increment for frames 0-4 (5 increments), held at 5 onwards
    assert result["exit_status"] == "ok"
    assert result["errors"] == []
    assert result["snapshots"][0]["values"]["x"] == 5


def test_axes_input():
    result = run_tool({
        "script": str(SCRIPTS / "axes_responder.py"),
        "frames": 5,
        "inputs": [{"frame": 2, "axes": {"GAMEPAD1_AXIS_LEFTX": 0.5}}],
        "snapshots": [{"frame": 4, "kind": "state", "attrs": ["last_x_axis"]}],
    })
    # Verify the script saw the axis value (modulo Pyxel's internal int range)
    assert result["exit_status"] == "ok"
    assert result["errors"] == []
    assert result["snapshots"][0]["values"]["last_x_axis"] != 0


@pytest.mark.skipif(not _mouse_simulation_supported(), reason="Pyxel version lacks mouse simulation API")
def test_mouse_pos_input():
    result = run_tool({
        "script": str(SCRIPTS / "mouse_responder.py"),
        "frames": 3,
        "inputs": [{"frame": 0, "mouse_pos": [42, 17]}],
        "snapshots": [{"frame": 2, "kind": "state", "attrs": ["last_x", "last_y"]}],
    })
    assert result["exit_status"] == "ok"
    assert result["errors"] == []
    assert result["snapshots"][0]["values"]["last_x"] == 42
    assert result["snapshots"][0]["values"]["last_y"] == 17


# --- Snapshot integration tests ---

def test_run_with_screen_image_snapshot(tmp_path):
    out = tmp_path / "f2.png"
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"frame": 2, "kind": "screen_image", "output": str(out)}],
    })
    assert result["exit_status"] == "ok"
    assert len(result["snapshots"]) == 1
    assert result["snapshots"][0]["frame"] == 2
    assert result["snapshots"][0]["kind"] == "screen_image"
    assert out.exists()


def test_run_with_screen_grid_snapshot():
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 3,
        "snapshots": [{"frame": 1, "kind": "screen_grid"}],
    })
    snap = result["snapshots"][0]
    assert snap["kind"] == "screen_grid"
    assert "grid" in snap


def test_run_with_state_snapshot():
    """stateful_app.App.update increments counter each frame.
    After 5 frames (f=0..4), update is called 5 times → counter == 5."""
    result = run_tool({
        "script": str(SCRIPTS / "stateful_app.py"),
        "frames": 5,
        "snapshots": [{"frame": 4, "kind": "state", "attrs": ["counter"]}],
    })
    assert result["snapshots"][0]["values"]["counter"] == 5


def test_run_with_layout_snapshot():
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 3,
        "snapshots": [{"frame": 1, "kind": "layout"}],
    })
    snap = result["snapshots"][0]
    assert snap["kind"] == "layout"
    assert "h_balance" in snap


def test_run_with_video_snapshot(tmp_path):
    out = tmp_path / "play.gif"
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 10,
        "snapshots": [{"kind": "video", "start_frame": 0, "end_frame": 10,
                       "fps": 30, "output": str(out)}],
    })
    assert out.exists()
    snap = result["snapshots"][0]
    assert snap["kind"] == "video"
    assert snap["frames_encoded"] == 10


def test_invalid_snapshot_kind_is_validation_error():
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 1,
        "snapshots": [{"frame": 0, "kind": "bogus"}],
    })
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


# --- Multi-frame snapshots ---

def test_multi_frame_screen_image(tmp_path):
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 10,
        "snapshots": [{
            "frames": "0:10:2",
            "kind": "screen_image",
            "output_pattern": str(tmp_path / "f-{frame}.png"),
        }],
    })
    assert result["exit_status"] == "ok"
    assert result["errors"] == []
    assert len(result["snapshots"]) == 5
    for r in result["snapshots"]:
        assert (tmp_path / f"f-{r['frame']:05d}.png").exists()


def test_multi_frame_state():
    result = run_tool({
        "script": str(SCRIPTS / "stateful_app.py"),
        "frames": 5,
        "snapshots": [{"frames": [1, 3], "kind": "state", "attrs": ["counter"]}],
    })
    assert result["exit_status"] == "ok"
    assert result["errors"] == []
    assert len(result["snapshots"]) == 2
    assert result["snapshots"][0]["frame"] == 1
    assert result["snapshots"][1]["frame"] == 3


def test_explicit_list_dedupe_warning():
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 10,
        "snapshots": [{"frames": [3, 1, 3], "kind": "state"}],
    })
    assert result["exit_status"] == "ok"
    assert result["errors"] == []
    # Dedupe + sort → [1, 3]
    assert len(result["snapshots"]) == 2
    # Warning must appear in log
    assert "sorted" in result["log"].lower()


# --- Frame-bounds validation tests ---

def test_snapshot_frame_out_of_bounds_is_validation_error():
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"frame": 99, "kind": "state"}],
    })
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_snapshot_negative_frame_is_validation_error():
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"frame": -1, "kind": "state"}],
    })
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_snapshot_frame_at_last_valid_index_passes():
    """frame == frames - 1 must be accepted (last valid index)."""
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"frame": 4, "kind": "state"}],
    })
    assert result["exit_status"] == "ok"


def test_snapshot_frame_equal_to_frames_is_validation_error():
    """frame == frames is out of range (0-based, strictly < frames)."""
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"frame": 5, "kind": "state"}],
    })
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_video_end_frame_exceeds_run_frames(tmp_path):
    out = tmp_path / "play.gif"
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"kind": "video", "start_frame": 0, "end_frame": 99,
                       "fps": 30, "output": str(out)}],
    })
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_video_start_geq_end_is_validation_error(tmp_path):
    out = tmp_path / "play.gif"
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"kind": "video", "start_frame": 3, "end_frame": 3,
                       "fps": 30, "output": str(out)}],
    })
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_video_negative_start_frame_is_validation_error(tmp_path):
    """start_frame < 0 must be rejected."""
    out = tmp_path / "play.gif"
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"kind": "video", "start_frame": -1, "end_frame": 5,
                       "fps": 30, "output": str(out)}],
    })
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_video_full_range_passes(tmp_path):
    """start_frame=0, end_frame=frames must pass (end_frame <= frames is allowed)."""
    out = tmp_path / "play.gif"
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "snapshots": [{"kind": "video", "start_frame": 0, "end_frame": 5,
                       "fps": 30, "output": str(out)}],
    })
    assert result["exit_status"] == "ok"
