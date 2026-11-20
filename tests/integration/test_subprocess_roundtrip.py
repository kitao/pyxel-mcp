import json
import subprocess
import sys

import pytest
from PIL import Image

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


@pytest.mark.parametrize(
    "fields",
    [
        {"frames": True},
        {"snapshots": [{"kind": "state"}]},
        {"snapshots": [{"kind": "state", "frame": 0, "unknown": 1}]},
        {"inputs": [{"frame": 0, "mouse_pos": [1]}]},
        {"inputs": [{"frame": 0, "buttons": ["init"]}]},
        {"inputs": [{"frame": 0, "axes": {"init": 0.5}}]},
    ],
)
def test_invalid_requests_are_rejected_before_script_execution(tmp_path, fields):
    marker = tmp_path / "executed"
    script = tmp_path / "game.py"
    script.write_text(f"from pathlib import Path\nPath({str(marker)!r}).touch()\n")

    result = _run("run", {"script": str(script), "frames": 1, **fields})

    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"
    assert not marker.exists()


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


@pytest.mark.parametrize(
    ("name", "attrs", "values", "inputs", "until"),
    [
        (
            "cube/c01_hello_cube",
            ["scene.camera.transform.pos.y"],
            {"scene.camera.transform.pos.y": 78.0},
            [],
            None,
        ),
        (
            "cube/c04_mesh_and_motion",
            ["gazelle.motion_index"],
            {"gazelle.motion_index": 1},
            [{"frame": 2, "buttons": ["KEY_2"]}],
            "gazelle.motion_index == 1",
        ),
    ],
)
def test_cube_examples_render_and_expose_state_in_a_fresh_process(
    tmp_path, name, attrs, values, inputs, until
):
    examples = {
        example["name"]: example for example in _run("pyxel_info", {})["examples"]
    }
    image_path = tmp_path / "cube.png"
    result = _run(
        "run",
        {
            "script": examples[name]["path"],
            "frames": 10 if until else 3,
            "inputs": inputs,
            "until": until,
            "snapshots": [
                {"kind": "state", "frame": "end", "attrs": attrs},
                {"kind": "screen_image", "frame": "end", "output": str(image_path)},
            ],
        },
    )

    assert result["ok"] is True, result["errors"]
    assert result["frame_count"] == 3
    if until:
        assert result["until_met"] is True
    assert result["snapshots"][0]["values"] == values
    with Image.open(image_path) as image:
        colors = image.getcolors(maxcolors=image.width * image.height)
        assert colors is not None and len(colors) > 1


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


@pytest.mark.parametrize("display", ["show", "flip"])
def test_bundled_static_screen_and_manual_animation(display):
    name = {"show": "05_color_palette", "flip": "99_flip_animation"}[display]
    entry = next(e for e in _run("pyxel_info", {})["examples"] if e["name"] == name)
    result = _run(
        "run",
        {
            "script": entry["path"],
            "frames": 3,
            "snapshots": [{"kind": "screen_grid", "frames": [0, 2]}],
        },
    )
    assert result["ok"] and result["frame_count"] == 3
    first, last = (snap["grid"] for snap in result["snapshots"])
    assert len({pixel for row in first for pixel in row}) > 1
    assert (first == last) == (display == "show")


@pytest.mark.parametrize("mode", ["run", "flip"])
def test_one_frame_inputs_and_held_buttons(tmp_path, mode):
    script = tmp_path / "inputs.py"
    body = (
        "pyxel.run(update, lambda: None)"
        if mode == "run"
        else "while True:\n    update()\n    pyxel.flip()"
    )
    script.write_text(
        "import pyxel\npyxel.init(8, 8)\n"
        "def update():\n"
        "    global text, paths, wheel, press\n"
        "    text, paths = pyxel.input_text, list(pyxel.dropped_files)\n"
        "    wheel = [pyxel.btnv(pyxel.MOUSE_WHEEL_X), pyxel.mouse_wheel]\n"
        "    press = [pyxel.btn(pyxel.KEY_A), pyxel.btnp(pyxel.KEY_A)]\n" + body
    )
    result = _run(
        "run",
        {
            "script": str(script),
            "frames": 2,
            "inputs": [
                {
                    "frame": 0,
                    "buttons": ["KEY_A"],
                    "input_text": "字",
                    "dropped_files": ["a.tmx"],
                    "mouse_wheel": [3, -2],
                }
            ],
            "snapshots": [
                {
                    "kind": "state",
                    "frames": "all",
                    "attrs": ["text", "paths", "wheel", "press"],
                }
            ],
        },
    )
    assert result["ok"], result["errors"]
    assert [s["values"] for s in result["snapshots"]] == [
        {"text": "字", "paths": ["a.tmx"], "wheel": [3, -2], "press": [True, True]},
        {"text": "", "paths": [], "wheel": [0, 0], "press": [True, False]},
    ]


@pytest.mark.parametrize("stop", ["pyxel.quit()", "pass", "raise ValueError('broken')"])
def test_manual_loop_keeps_only_presented_frame(tmp_path, stop):
    script = tmp_path / "finite.py"
    script.write_text(
        f"import pyxel\npyxel.init(8, 8)\nn = 1\npyxel.cls(4)\npyxel.flip()\nn = 2\npyxel.cls(5)\n{stop}\n"
    )
    result = _run(
        "run",
        {
            "script": str(script),
            "frames": 3,
            "snapshots": [
                {"kind": "state", "frame": "end", "attrs": ["n"]},
                {"kind": "screen_grid", "frame": "end", "bbox": [0, 0, 1, 1]},
            ],
        },
    )
    assert result["frame_count"] == 1
    if stop.startswith("raise"):
        assert result["errors"][0]["phase"] == "game_loop"
        assert result["errors"][0]["frame"] == 1
    else:
        assert result["ok"], result["errors"]
        state, grid = result["snapshots"]
        assert state["values"] == {"n": 1}
        assert grid["grid"] == [[4]]


def test_stall_requires_all_signals_on_consecutive_frames(tmp_path):
    script = tmp_path / "progress.py"
    script.write_text(
        "import pyxel\npyxel.init(8, 8)\nfor n in range(5):\n    pyxel.cls(3)\n    pyxel.flip()\n"
    )
    result = _run(
        "run",
        {
            "script": str(script),
            "frames": 5,
            "stall_window_frames": 2,
            "snapshots": [
                {"kind": "screen_grid", "bbox": [0, 0, 1, 1], "frames": "all"},
                {"kind": "state", "attrs": ["n"], "frames": "all"},
            ],
        },
    )
    assert result["ok"] and result["frame_count"] == 5
    sparse = _run(
        "run",
        {
            "script": str(script),
            "frames": 5,
            "stall_window_frames": 2,
            "snapshots": [{"kind": "screen_grid", "frames": [0, 2, 4]}],
        },
    )
    assert sparse["ok"] and sparse["frame_count"] == 5


def test_short_palette_matches_native_png_in_all_renders(tmp_path):
    script = tmp_path / "short_palette.py"
    script.write_text(
        "import pyxel\npyxel.init(8, 8)\npyxel.images[0].cls(12)\n"
        "pyxel.colors[:] = [0, 0xABCDEF]\npyxel.colors = [0xFF0000]\n"
        "pyxel.run(lambda: None, lambda: pyxel.cls(12))"
    )
    native = tmp_path / "live.png.png"
    end = tmp_path / "end.png"
    video = tmp_path / "clip.gif"
    result = _run(
        "run",
        {
            "script": str(script),
            "frames": 1,
            "snapshots": [
                {"kind": "screen_image", "frame": 0, "output": str(native)},
                {"kind": "screen_image", "frame": "end", "output": str(end)},
                {
                    "kind": "video",
                    "start_frame": 0,
                    "end_frame": 1,
                    "output": str(video),
                },
            ],
        },
    )
    assert result["ok"], result["errors"]
    palette = _run("read_palette", {"script": str(script)})
    assert palette["colors"] == {"0": "#000000", "1": "#abcdef"}
    renders = [native, end, video]
    for tool, args in [
        ("read_image", {"image": 0, "w": 8, "h": 8}),
        ("read_tilemap", {"tilemap": 0, "bbox": [0, 0, 1, 1]}),
    ]:
        path = tmp_path / f"{tool}.png"
        assert _run(tool, {"script": str(script), "render_path": str(path), **args})[
            "ok"
        ]
        renders.append(path)
    for path in renders:
        with Image.open(path) as image:
            assert image.size == (8, 8)
            assert image.convert("RGB").getcolors() == [(64, (0xAB, 0xCD, 0xEF))]


def test_bundled_platformer_can_stop_on_its_module_level_player():
    path = next(
        e["path"]
        for e in _run("pyxel_info", {})["examples"]
        if e["name"] == "10_platformer"
    )
    scenario = {
        "script": path,
        "frames": 30,
        "until": "__main__.player.x >= 5",
        "snapshots": [
            {"kind": "state", "frame": "end", "attrs": ["__main__.player.x"]}
        ],
    }
    waiting = _run("run", scenario)
    moving = _run(
        "run", {**scenario, "inputs": [{"frame": 0, "buttons": ["KEY_RIGHT"]}]}
    )
    assert waiting["ok"] and waiting["until_met"] is False
    assert waiting["snapshots"][0]["values"]["__main__.player.x"] == 0
    assert moving["ok"] and moving["until_met"] is True and moving["frame_count"] < 30
    assert moving["snapshots"][0]["values"]["__main__.player.x"] >= 5
