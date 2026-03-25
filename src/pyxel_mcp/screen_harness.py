"""Screen pixel capture harness - captures screen as color index grid.

Runs a Pyxel script and at each target frame reads every screen pixel
with pyxel.pget(), outputting a JSON array of {frame, width, height, grid}.

Usage:
    python screen_harness.py <script> <frame_list_csv>
"""

import json
import os
import sys

if len(sys.argv) < 3:
    print(
        "Usage: screen_harness <script> <frame_list_csv>",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
frame_list = sorted(set(max(1, int(f)) for f in sys.argv[2].split(",")))

import pyxel

from pyxel_mcp._headless import patch_game_loop, run_script, setup_harness

setup_harness(script_path)

_results = []
_capture_idx = 0


def _read_screen():
    """Read all screen pixels as a 2D color index grid."""
    w, h = pyxel.width, pyxel.height
    grid = []
    for y in range(h):
        grid.append([pyxel.pget(x, y) for x in range(w)])
    return {"frame": pyxel.frame_count, "width": w, "height": h, "grid": grid}


def _on_frame(fc, draw):
    global _capture_idx
    if _capture_idx >= len(frame_list):
        return False
    if fc < frame_list[_capture_idx]:
        return False
    draw()
    _results.append(_read_screen())
    _capture_idx += 1
    if _capture_idx >= len(frame_list):
        print(json.dumps(_results))
        sys.stdout.flush()
        return True
    return False


def _on_show():
    _results.append(_read_screen())
    print(json.dumps(_results))
    sys.stdout.flush()


patch_game_loop(_on_frame, on_show=_on_show)
run_script(script_path)
