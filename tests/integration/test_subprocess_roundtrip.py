import json
import subprocess
import sys

import pytest

from tests.conftest import SCRIPTS


def _run(subcommand: str, payload: dict) -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pyxel_mcp.observe._harnesses.main", subcommand],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert proc.returncode == 0, f"stderr: {proc.stderr}"
    return json.loads(proc.stdout)


def test_validate_via_subprocess():
    result = _run("validate", {"script": str(SCRIPTS / "minimal.py")})
    assert result["ok"] is True


def test_frames_run_before_the_script_can_reach_post_run_code(tmp_path):
    script = tmp_path / "post_run.py"
    script.write_text(
        "import pyxel\n"
        "pyxel.init(8, 8)\n"
        "counter = 0\n"
        "def update():\n"
        "    global counter\n"
        "    counter += 1\n"
        "pyxel.run(update, lambda: pyxel.cls(1))\n"
        "raise RuntimeError('post-run code must not execute')\n"
    )

    result = _run(
        "run",
        {
            "script": str(script),
            "frames": 3,
            "snapshots": [{"kind": "state", "frame": "end", "attrs": ["counter"]}],
        },
    )

    assert result["ok"] is True, result["errors"]
    assert result["snapshots"][0]["values"] == {"counter": 3}


def test_pyxel_info_via_subprocess():
    result = _run("pyxel_info", {})
    assert "pyxel_version" in result
    assert result["resources"]["run_snapshots_schema"] == "pyxel://run-snapshots-schema"


def test_relative_asset_paths_resolve_from_the_script_directory():
    """`pyxel.load("assets/...")` must work exactly as under `python game.py`."""
    result = _run(
        "run",
        {
            "script": str(SCRIPTS / "relative_asset.py"),
            "frames": 1,
            "snapshots": [{"kind": "state", "frame": 0, "attrs": ["loaded_color"]}],
        },
    )
    assert result["exit_status"] == "ok", result["errors"]
    assert result["snapshots"][0]["values"]["loaded_color"] != 0


def test_read_tools_share_the_script_context():
    result = _run("read_palette", {"script": str(SCRIPTS / "relative_asset.py")})
    assert result["ok"] is True, result["errors"]


def test_script_is_registered_as_main_during_import_and_game_loop(tmp_path):
    script = tmp_path / "main_context.py"
    script.write_text(
        """from __future__ import annotations
from dataclasses import dataclass, fields
from typing import ClassVar
import __main__
import pickle
import pyxel

@dataclass
class Player:
    shared: ClassVar[int] = 7
    score: int = 1

field_names = [field.name for field in fields(Player)]
player = Player()
identity_matches = False
restored_score = 0

def update():
    global identity_matches, restored_score
    identity_matches = __main__.player is player
    restored_score = pickle.loads(pickle.dumps(player)).score

pyxel.init(16, 16)
pyxel.run(update, lambda: pyxel.cls(0))
"""
    )
    result = _run(
        "run",
        {
            "script": str(script),
            "frames": 1,
            "snapshots": [
                {
                    "kind": "state",
                    "frame": "end",
                    "attrs": ["field_names", "identity_matches", "restored_score"],
                }
            ],
        },
    )
    assert result["ok"] is True, result["errors"]
    assert result["snapshots"][0]["values"] == {
        "field_names": ["score"],
        "identity_matches": True,
        "restored_score": 1,
    }


def test_axes_replacement_and_empty_map_release_engine_values(tmp_path):
    script = tmp_path / "axes.py"
    script.write_text(
        """import pyxel
left = []
right = []
def update():
    left.append(pyxel.btnv(pyxel.GAMEPAD1_AXIS_LEFTX))
    right.append(pyxel.btnv(pyxel.GAMEPAD1_AXIS_RIGHTX))
pyxel.init(16, 16)
pyxel.run(update, lambda: pyxel.cls(0))
"""
    )
    result = _run(
        "run",
        {
            "script": str(script),
            "frames": 5,
            "inputs": [
                {"frame": 0, "axes": {"GAMEPAD1_AXIS_LEFTX": 1.0}},
                {"frame": 1, "buttons": []},
                {"frame": 2, "axes": {"GAMEPAD1_AXIS_RIGHTX": -1.0}},
                {"frame": 3, "axes": {}},
            ],
            "snapshots": [
                {"kind": "state", "frame": "end", "attrs": ["left", "right"]}
            ],
        },
    )
    assert result["ok"] is True, result["errors"]
    assert result["snapshots"][0]["values"] == {
        "left": [32767, 32767, 0, 0, 0],
        "right": [0, 0, -32767, 0, 0],
    }


@pytest.mark.parametrize(
    "init_args",
    [
        "16, 16, 'Positional', 30",
        "16, 16, 'Positional', 30, pyxel.KEY_NONE, None, 2, 10, False",
    ],
)
def test_positional_init_arguments_remain_supported(tmp_path, init_args):
    script = tmp_path / "positional_init.py"
    script.write_text(
        f"import pyxel\npyxel.init({init_args})\n"
        "pyxel.run(lambda: None, lambda: pyxel.cls(0))\n"
    )
    result = _run("run", {"script": str(script), "frames": 2})
    assert result["ok"] is True, result["errors"]
    assert result["frame_count"] == 2


@pytest.mark.parametrize("encoding", ["latin-1", "utf-8-sig"])
def test_script_source_encoding_matches_python(tmp_path, encoding):
    script = tmp_path / "encoded.py"
    coding = "latin-1" if encoding == "latin-1" else "utf-8"
    script.write_bytes(
        (
            f"# coding: {coding}\nimport pyxel\nmessage = 'caf\u00e9'\n"
            "pyxel.init(16, 16)\n"
            "pyxel.run(lambda: None, lambda: pyxel.cls(0))\n"
        ).encode(encoding)
    )
    result = _run(
        "run",
        {
            "script": str(script),
            "frames": 1,
            "snapshots": [{"kind": "state", "frame": "end", "attrs": ["message"]}],
        },
    )
    assert result["ok"] is True, result["errors"]
    assert result["snapshots"][0]["values"]["message"] == "caf\u00e9"


def test_bundled_pyxel_example_runs_with_its_assets():
    info = _run("pyxel_info", {})
    hello = next((e for e in info["examples"] if e["name"] == "01_hello_pyxel"), None)
    if hello is None:
        pytest.skip("01_hello_pyxel is not bundled with this Pyxel build")

    result = _run("run", {"script": hello["path"], "frames": 2})
    assert result["exit_status"] == "ok", result["errors"]
