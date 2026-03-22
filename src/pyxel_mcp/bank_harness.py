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

sys.argv = [script_path]

import pyxel

from pyxel_mcp._headless import patch_headless_init, run_script

# Force 256x256 screen for full bank capture
patch_headless_init(script_path, transform_args=lambda args: (256, 256) + args[2:])

_captured = False


def _capture_bank():
    global _captured
    if _captured:
        return
    _captured = True

    # Draw the image bank to screen
    pyxel.cls(0)
    pyxel.blt(0, 0, bank_index, 0, 0, 256, 256)

    try:
        pyxel.screenshot(output_path, scale=capture_scale)
    except Exception as e:
        print(f"Capture error: {e}", file=sys.stderr)
    pyxel.quit()
    os._exit(0)


# Patch pyxel.run: capture at frame 1
_original_run = pyxel.run


def _patched_run(update, draw):
    def wrapped_update():
        update()
        _capture_bank()

    _original_run(wrapped_update, draw)


pyxel.run = _patched_run

# Patch pyxel.show
_original_show = pyxel.show
pyxel.show = lambda: _capture_bank()

# Patch pyxel.flip
_original_flip = pyxel.flip


def _patched_flip():
    _original_flip()
    _capture_bank()


pyxel.flip = _patched_flip

# Execute
run_script(script_path)
