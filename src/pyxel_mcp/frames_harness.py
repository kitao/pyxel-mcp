"""Multi-frame capture harness - captures screenshots at multiple frame points.

Runs a Pyxel script and saves screenshots at each specified frame number.

Usage:
    python frames_harness.py <script> <output_dir> <frame_list_csv> <scale>
"""

import os
import sys

if len(sys.argv) < 5:
    print(
        "Usage: frames_harness <script> <output_dir> <frame_csv> <scale>",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
output_dir = os.path.abspath(sys.argv[2])
frame_list = sorted(int(f) for f in sys.argv[3].split(","))
capture_scale = int(sys.argv[4])

import pyxel

from pyxel_mcp._headless import patch_game_loop, run_script, setup_harness

setup_harness(script_path)

_capture_idx = 0


def _on_frame(fc, draw):
    """Capture at the current frame if it matches the next target."""
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


patch_game_loop(_on_frame, on_show=_on_show)
run_script(script_path)
