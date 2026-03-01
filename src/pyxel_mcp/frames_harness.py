"""Multi-frame capture harness - captures screenshots at multiple frame points.

Runs a Pyxel script and saves screenshots at each specified frame number.

Usage:
    python frames_harness.py <script> <output_dir> <frame_list_csv> <scale>
"""

import os
import runpy
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

sys.argv = [script_path]

import pyxel

_captured = set()
_max_frame = max(frame_list)
_frame_set = set(frame_list)


def _try_capture():
    """Capture current frame if it's in the target list."""
    fc = pyxel.frame_count
    if fc in _frame_set and fc not in _captured:
        path = os.path.join(output_dir, f"frame_{fc:04d}.png")
        try:
            pyxel.screen.save(path, capture_scale)
        except Exception as e:
            print(f"Capture error at frame {fc}: {e}", file=sys.stderr)
        _captured.add(fc)
    if len(_captured) >= len(frame_list):
        pyxel.quit()


# Patch pyxel.run: wrap update to capture at target frames
_original_run = pyxel.run


def _patched_run(update, draw):
    def wrapped_update():
        update()
        _try_capture()

    _original_run(wrapped_update, draw)


pyxel.run = _patched_run

# Patch pyxel.show: capture as frame 0
_original_show = pyxel.show


def _patched_show():
    path = os.path.join(output_dir, "frame_show.png")
    try:
        pyxel.screen.save(path, capture_scale)
    except Exception as e:
        print(f"Capture error: {e}", file=sys.stderr)
    pyxel.quit()


pyxel.show = _patched_show

# Patch pyxel.flip: count flips and capture
_flip_counter = 0
_original_flip = pyxel.flip


def _patched_flip():
    global _flip_counter
    _original_flip()
    _flip_counter += 1
    if _flip_counter in _frame_set and _flip_counter not in _captured:
        path = os.path.join(output_dir, f"frame_{_flip_counter:04d}.png")
        try:
            pyxel.screen.save(path, capture_scale)
        except Exception as e:
            print(f"Capture error at flip {_flip_counter}: {e}", file=sys.stderr)
        _captured.add(_flip_counter)
    if len(_captured) >= len(frame_list):
        pyxel.quit()


pyxel.flip = _patched_flip

# Execute the user script
sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass
