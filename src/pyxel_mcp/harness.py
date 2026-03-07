"""Execution harness for capturing Pyxel screenshots.

Runs a Pyxel script as a subprocess, monkey-patching pyxel.run(),
pyxel.show(), and pyxel.flip() to automatically capture a screenshot
after a specified number of frames and then quit.

Usage:
    python -m pyxel_mcp.harness <script_path> <output_path> <frames> <scale>
"""

import os
import runpy
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

# Reset argv so the user script sees itself as __main__
sys.argv = [script_path]

import pyxel

# Turbo mode: override FPS to run as fast as possible
_original_init = pyxel.init


def _turbo_init(*args, **kwargs):
    kwargs["fps"] = 10000
    _original_init(*args, **kwargs)
    # pyxel.init() chdir's to the caller's directory via inspect.stack(),
    # but under runpy that resolves to the harness, not the user script.
    os.chdir(os.path.dirname(script_path) or ".")


pyxel.init = _turbo_init

_frame_counter = 0
_captured = False


def _capture_and_quit():
    """Save the current screen and exit."""
    global _captured
    if _captured:
        return
    _captured = True
    try:
        pyxel.screen.save(output_path, capture_scale)
    except Exception as e:
        print(f"Capture error: {e}", file=sys.stderr)
    pyxel.quit()


# Patch pyxel.run: wrap draw to capture after rendering the target frame
_original_run = pyxel.run


def _patched_run(update, draw):
    def wrapped_draw():
        if pyxel.frame_count >= target_frames:
            draw()
            _capture_and_quit()

    _original_run(update, wrapped_draw)


pyxel.run = _patched_run

# Patch pyxel.show: capture immediately when show() is called
_original_show = pyxel.show


def _patched_show():
    _capture_and_quit()


pyxel.show = _patched_show

# Patch pyxel.flip: count flip calls and auto-capture
_original_flip = pyxel.flip


def _patched_flip():
    global _frame_counter
    _original_flip()
    _frame_counter += 1
    if _frame_counter >= target_frames:
        _capture_and_quit()


pyxel.flip = _patched_flip

# Execute the user script
sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass
