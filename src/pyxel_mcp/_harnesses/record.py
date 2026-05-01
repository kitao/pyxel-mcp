"""Record gameplay harness — runs a Pyxel script and saves screencast as GIF.

Usage:
    python -m pyxel_mcp._harnesses.record <script> <output_gif> <duration> <scale> <input_file>

Where input_file contains a JSON list of frame events compatible with
the input harness format (with optional `btnv` field).
"""

import json
import os
import sys

if len(sys.argv) < 6:
    print(
        "Usage: record <script> <output_gif> <duration> <scale> <input_file>",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
output_gif = os.path.abspath(sys.argv[2])
duration = int(sys.argv[3])
capture_scale = int(sys.argv[4])
input_file = os.path.abspath(sys.argv[5])

with open(input_file) as f:
    input_schedule = sorted(json.load(f), key=lambda e: e["frame"])

import pyxel

from pyxel_mcp._common.headless import patch_game_loop, run_script, setup_harness

setup_harness(script_path)

_schedule_idx = 0
_active_keys = set()


def _resolve_key(name):
    val = getattr(pyxel, name, None)
    if val is None:
        raise ValueError(f"Unknown key: {name}")
    return val


def _apply_input():
    global _schedule_idx, _active_keys
    fc = pyxel.frame_count
    while _schedule_idx < len(input_schedule):
        entry = input_schedule[_schedule_idx]
        if entry["frame"] > fc:
            break
        new_keys = set(_resolve_key(k) for k in entry.get("keys", []))
        for key in _active_keys - new_keys:
            pyxel.set_btn(key, False)
        for key in new_keys - _active_keys:
            pyxel.set_btn(key, True)
        _active_keys = new_keys
        for name, val in entry.get("btnv", {}).items():
            pyxel.set_btnv(_resolve_key(name), int(val))
        if "mouse_x" in entry or "mouse_y" in entry:
            mx = entry.get("mouse_x", pyxel.mouse_x)
            my = entry.get("mouse_y", pyxel.mouse_y)
            pyxel.set_mouse_pos(mx, my)
        _schedule_idx += 1


def _save_gif():
    # screencast() appends ".gif" automatically; strip if present
    base = output_gif[:-4] if output_gif.endswith(".gif") else output_gif
    pyxel.screencast(base, scale=capture_scale)


def _on_frame(fc, draw):
    if fc < duration:
        return False
    draw()
    _save_gif()
    return True


def _on_show():
    _save_gif()


patch_game_loop(_on_frame, on_show=_on_show, pre_update=_apply_input)
run_script(script_path)
