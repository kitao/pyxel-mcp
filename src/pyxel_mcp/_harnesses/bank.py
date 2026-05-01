"""Image bank harness - renders entire image bank as a screenshot.

Runs a Pyxel script to populate image banks, then overrides the screen
to 256x256 and draws the requested bank for capture.

Usage:
    python bank_harness.py <script> <output_path> [bank_index] [scale]
"""

import os
import sys

if len(sys.argv) < 3:
    print(
        "Usage: bank_harness <script> <output_path> [bank_index] [scale]",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
output_path = os.path.abspath(sys.argv[2])
bank_index = int(sys.argv[3]) if len(sys.argv) > 3 else 0
capture_scale = int(sys.argv[4]) if len(sys.argv) > 4 else 1

import pyxel

from pyxel_mcp._common.headless import patch_game_loop, run_script, setup_harness

# Force 256x256 screen for full bank capture
setup_harness(script_path, transform_args=lambda args: (256, 256) + args[2:])

_captured = False


def _capture_bank(fc, draw):
    global _captured
    if _captured:
        return False
    _captured = True

    # Draw the image bank to screen
    pyxel.cls(0)
    pyxel.blt(0, 0, bank_index, 0, 0, 256, 256)

    try:
        pyxel.screenshot(output_path, scale=capture_scale)
    except Exception as e:
        print(f"Capture error: {e}", file=sys.stderr)
    return True


patch_game_loop(_capture_bank, on_show=lambda: _capture_bank(0, lambda: None))
run_script(script_path)
