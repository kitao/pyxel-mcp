"""Script diagnostics must never be mistaken for the harness result."""

import json

import pytest

from pyxel_mcp.dispatch import dispatch
from pyxel_mcp.server import read_palette, run
from tests.conftest import structured


@pytest.mark.parametrize("diagnostic", ["123", "{}", '{"ok":false,"errors":[]}'])
@pytest.mark.parametrize("tool", ["run", "read_palette"])
def test_exit_handler_json_does_not_replace_tool_result(tmp_path, diagnostic, tool):
    script = tmp_path / "game.py"
    script.write_text(
        "import atexit\n"
        "import pyxel\n"
        f"atexit.register(lambda: print({diagnostic!r}))\n"
        "pyxel.init(8, 8)\n"
        "pyxel.run(lambda: None, lambda: pyxel.cls(1))\n"
    )

    if tool == "run":
        result = structured(run(script=str(script), frames=2))
        assert result["frame_count"] == 2
        assert result["log"].strip() == diagnostic
    else:
        result = structured(read_palette(script=str(script)))
        assert result["palette_size"] >= 16
    assert result["ok"] is True
    assert result["errors"] == []


def test_native_non_utf8_diagnostics_stay_in_log(tmp_path):
    script = tmp_path / "game.py"
    script.write_text(
        "import os\n"
        "import pyxel\n"
        "os.write(1, b'output: \\xff\\n')\n"
        "os.write(2, b'error: \\xff\\n')\n"
        "pyxel.init(8, 8)\n"
        "pyxel.run(lambda: None, lambda: pyxel.cls(1))\n"
    )

    result = structured(run(script=str(script), frames=1))

    assert result["ok"] is True
    assert "output: \ufffd" in result["log"]
    assert "error: \ufffd" in result["log"]
    json.dumps(result, allow_nan=False)


def test_script_cannot_supply_a_result_by_printing_json_and_exiting(tmp_path):
    script = tmp_path / "game.py"
    script.write_text('print(\'{"ok":true,"errors":[]}\')\nraise SystemExit(0)\n')

    result = dispatch("read_palette", {"script": str(script)})

    assert result["ok"] is False
    assert "no JSON payload" in result["errors"][0]["message"]
