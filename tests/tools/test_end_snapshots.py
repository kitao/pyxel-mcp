"""`"frame": "end"` snapshot token tests."""
from tests.conftest import SCRIPTS
from pyxel_mcp.observe._harnesses.tools.run import run as run_tool

STATEFUL = str(SCRIPTS / "stateful_app.py")


def test_end_state_snapshot_fires_at_frame_cap():
    result = run_tool({
        "script": STATEFUL, "frames": 5,
        "snapshots": [{"kind": "state", "frame": "end", "attrs": ["counter"]}],
    })
    assert result["ok"] is True
    snap = result["snapshots"][0]
    assert snap["frame"] == 4
    assert snap["values"]["counter"] == 5


def test_end_snapshots_fire_at_until_frame(tmp_path):
    out = tmp_path / "end.png"
    result = run_tool({
        "script": STATEFUL, "frames": 100, "until": "counter >= 2",
        "snapshots": [
            {"kind": "state", "frame": "end", "attrs": ["counter"]},
            {"kind": "screen_image", "frame": "end", "output": str(out)},
        ],
    })
    assert result["until_met"] is True
    state_snap = next(s for s in result["snapshots"] if s["kind"] == "state")
    assert state_snap["frame"] == 1
    assert state_snap["values"]["counter"] == 2
    assert out.exists()


def test_end_snapshot_skipped_on_import_crash():
    result = run_tool({
        "script": str(SCRIPTS / "crashing_init.py"), "frames": 5,
        "snapshots": [{"kind": "state", "frame": "end"}],
    })
    assert result["ok"] is False
    assert result["snapshots"] == []


def test_other_frame_strings_still_rejected():
    result = run_tool({
        "script": STATEFUL, "frames": 5,
        "snapshots": [{"kind": "state", "frame": "final"}],
    })
    assert result["ok"] is False
    assert result["exit_status"] == "invalid"
