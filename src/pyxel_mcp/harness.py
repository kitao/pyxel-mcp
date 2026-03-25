"""Execution harness for capturing Pyxel screenshots.

Runs a Pyxel script as a subprocess, monkey-patching pyxel.run(),
pyxel.show(), and pyxel.flip() to automatically capture a screenshot
after a specified number of frames and then quit.

Usage:
    python -m pyxel_mcp.harness <script_path> <output_path> <frames> <scale>
"""

import os
import sys

# Parse arguments before importing pyxel (avoids SDL init issues)
if len(sys.argv) < 5:
    print("Usage: python -m pyxel_mcp.harness <script> <output> <frames> <scale>",
          file=sys.stderr)
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
output_path = os.path.abspath(sys.argv[2])
target_frames = int(sys.argv[3])
capture_scale = int(sys.argv[4])

import pyxel

from pyxel_mcp._headless import patch_game_loop, run_script, setup_harness

setup_harness(script_path)

_captured = False


def _on_frame(fc, draw):
    global _captured
    if _captured or fc < target_frames:
        return False
    _captured = True
    draw()
    try:
        pyxel.screenshot(output_path, scale=capture_scale)
    except Exception as e:
        print(f"Capture error: {e}", file=sys.stderr)
    return True


patch_game_loop(_on_frame)
run_script(script_path)
