"""`"frame": "end"` snapshot token tests."""

from pyxel_mcp.observe._harnesses.tools.run import run as run_tool
from tests.conftest import SCRIPTS

STATEFUL = str(SCRIPTS / "stateful_app.py")


def test_end_state_snapshot_fires_at_frame_cap():
    result = run_tool(
        {
            "script": STATEFUL,
            "frames": 5,
            "snapshots": [{"kind": "state", "frame": "end", "attrs": ["counter"]}],
        }
    )
    assert result["ok"] is True
    snap = result["snapshots"][0]
    assert snap["frame"] == 4
    assert snap["values"]["counter"] == 5


def test_end_snapshots_fire_at_until_frame(tmp_path):
    out = tmp_path / "end.png"
    result = run_tool(
        {
            "script": STATEFUL,
            "frames": 100,
            "until": "counter >= 2",
            "snapshots": [
                {"kind": "state", "frame": "end", "attrs": ["counter"]},
                {"kind": "screen_image", "frame": "end", "output": str(out)},
            ],
        }
    )
    assert result["until_met"] is True
    state_snap = next(s for s in result["snapshots"] if s["kind"] == "state")
    assert state_snap["frame"] == 1
    assert state_snap["values"]["counter"] == 2
    assert out.exists()


def test_end_snapshot_skipped_on_import_crash():
    result = run_tool(
        {
            "script": str(SCRIPTS / "crashing_init.py"),
            "frames": 5,
            "snapshots": [{"kind": "state", "frame": "end"}],
        }
    )
    assert result["ok"] is False
    assert result["snapshots"] == []


def test_other_frame_strings_still_rejected():
    result = run_tool(
        {
            "script": STATEFUL,
            "frames": 5,
            "snapshots": [{"kind": "state", "frame": "final"}],
        }
    )
    assert result["ok"] is False
    assert result["exit_status"] == "invalid"


def test_end_property_error_on_an_earlier_frame_does_not_fail_the_run(tmp_path):
    script = tmp_path / "late_property.py"
    script.write_text(
        "import pyxel\n"
        "class App:\n"
        "    def __init__(self):\n"
        "        self.counter = 0\n"
        "        pyxel.init(8, 8)\n"
        "        pyxel.run(self.update, lambda: pyxel.cls(1))\n"
        "    def update(self):\n"
        "        self.counter += 1\n"
        "    @property\n"
        "    def value(self):\n"
        "        if self.counter < 3:\n"
        "            raise ValueError('not ready')\n"
        "        return self.counter\n"
        "App()\n"
    )

    result = run_tool(
        {
            "script": str(script),
            "frames": 3,
            "snapshots": [{"kind": "state", "frame": "end", "attrs": ["value"]}],
        }
    )

    assert result["ok"] is True, result["errors"]
    assert result["snapshots"][0]["values"] == {"value": 3}
