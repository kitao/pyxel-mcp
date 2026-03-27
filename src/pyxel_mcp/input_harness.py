"""Input simulation harness - simulates key/mouse input and captures screenshots.

Runs a Pyxel script with simulated input events at specified frames and saves
screenshots at each capture frame.

Usage:
    python input_harness.py <script> <output_dir> <capture_csv> <scale> <input_file>
"""

import json
import os
import sys

if len(sys.argv) < 6:
    print(
        "Usage: input_harness <script> <output_dir> <capture_csv> <scale> <input_file>",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
output_dir = os.path.abspath(sys.argv[2])
frame_list = sorted(int(f) for f in sys.argv[3].split(","))
capture_scale = int(sys.argv[4])
input_file = os.path.abspath(sys.argv[5])

with open(input_file) as f:
    input_schedule = sorted(json.load(f), key=lambda e: e["frame"])

import pyxel

from pyxel_mcp._headless import patch_game_loop, run_script, setup_harness

setup_harness(script_path)

# --- Input simulation state ---

_schedule_idx = 0
_active_keys = set()
_capture_idx = 0


def _resolve_key(name):
    """Convert key name like 'KEY_SPACE' to pyxel constant."""
    val = getattr(pyxel, name, None)
    if val is None:
        raise ValueError(f"Unknown key: {name}")
    return val


def _apply_input():
    """Apply scheduled input events up to the current frame."""
    global _schedule_idx, _active_keys

    fc = pyxel.frame_count
    while _schedule_idx < len(input_schedule):
        entry = input_schedule[_schedule_idx]
        if entry["frame"] > fc:
            break

        new_keys = set(_resolve_key(k) for k in entry.get("keys", []))

        # Release keys no longer held
        for key in _active_keys - new_keys:
            pyxel.set_btn(key, False)

        # Press newly held keys
        for key in new_keys - _active_keys:
            pyxel.set_btn(key, True)

        _active_keys = new_keys

        # Set mouse position if specified
        if "mouse_x" in entry or "mouse_y" in entry:
            mx = entry.get("mouse_x", pyxel.mouse_x)
            my = entry.get("mouse_y", pyxel.mouse_y)
            pyxel.set_mouse_pos(mx, my)

        _schedule_idx += 1


def _on_frame(fc, draw):
    """Capture screenshot at target frames."""
    global _capture_idx
    if _capture_idx >= len(frame_list):
        return False
    target = frame_list[_capture_idx]
    if fc < target:
        return False
    draw()
    path = os.path.join(output_dir, f"frame_{target:04d}.png")
    try:
        pyxel.screenshot(path, scale=capture_scale)
    except Exception as e:
        print(f"Capture error at frame {target}: {e}", file=sys.stderr)
    _capture_idx += 1
    return _capture_idx >= len(frame_list)


def _on_show():
    path = os.path.join(output_dir, "frame_show.png")
    try:
        pyxel.screenshot(path, scale=capture_scale)
    except Exception as e:
        print(f"Capture error: {e}", file=sys.stderr)


patch_game_loop(_on_frame, on_show=_on_show, pre_update=_apply_input)
run_script(script_path)
