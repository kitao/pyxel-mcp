"""Verify play_and_capture forwards btnv events to set_btnv."""

import pytest


@pytest.fixture
def axis_reader_script(tmp_path):
    """Pyxel script that records GAMEPAD1_AXIS_LEFTX value at frame 30."""
    script = tmp_path / "axis.py"
    script.write_text(
        """
import pyxel

class App:
    def __init__(self):
        pyxel.init(32, 32)
        self.axis_value = 0
        pyxel.run(self.update, self.draw)

    def update(self):
        if pyxel.frame_count == 30:
            self.axis_value = pyxel.btnv(pyxel.GAMEPAD1_AXIS_LEFTX)
            with open("axis_value.txt", "w") as f:
                f.write(str(self.axis_value))

    def draw(self):
        pyxel.cls(0)

App()
"""
    )
    return str(script)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_btnv_forwarded_to_pyxel(axis_reader_script, tmp_path, monkeypatch):
    """Setting btnv at frame 25 should be observable by pyxel.btnv() at frame 30."""
    monkeypatch.chdir(tmp_path)

    from pyxel_mcp._tools.run import _play_and_capture_impl

    inputs = '[{"frame":25, "btnv":{"GAMEPAD1_AXIS_LEFTX": 16384}}]'

    await _play_and_capture_impl(
        axis_reader_script, inputs=inputs, frames="31", scale=1, timeout=15
    )

    axis_file = tmp_path / "axis_value.txt"
    assert axis_file.exists(), "script did not write axis value"
    assert axis_file.read_text().strip() == "16384"
