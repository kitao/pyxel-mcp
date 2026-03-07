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

# Turbo mode: override FPS to run as fast as possible
_original_init = pyxel.init


def _turbo_init(*args, **kwargs):
    kwargs["fps"] = 10000
    _original_init(*args, **kwargs)
    os.chdir(os.path.dirname(script_path) or ".")


pyxel.init = _turbo_init

_capture_idx = 0  # index into frame_list (sorted)


def _try_capture_next(draw):
    """Capture for the next target frame if frame_count has reached it."""
    global _capture_idx
    if _capture_idx >= len(frame_list):
        pyxel.quit()
        return
    fc = pyxel.frame_count
    target = frame_list[_capture_idx]
    if fc >= target:
        draw()
        path = os.path.join(output_dir, f"frame_{target:04d}.png")
        try:
            pyxel.screen.save(path, capture_scale)
        except Exception as e:
            print(f"Capture error at frame {target}: {e}", file=sys.stderr)
        _capture_idx += 1
        if _capture_idx >= len(frame_list):
            pyxel.quit()


# Patch pyxel.run: wrap draw to capture after rendering target frames
_original_run = pyxel.run


def _patched_run(update, draw):
    def wrapped_draw():
        _try_capture_next(draw)

    _original_run(update, wrapped_draw)


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
_flip_capture_idx = 0
_original_flip = pyxel.flip


def _patched_flip():
    global _flip_counter, _flip_capture_idx
    _original_flip()
    _flip_counter += 1
    if _flip_capture_idx < len(frame_list) and _flip_counter >= frame_list[_flip_capture_idx]:
        target = frame_list[_flip_capture_idx]
        path = os.path.join(output_dir, f"frame_{target:04d}.png")
        try:
            pyxel.screen.save(path, capture_scale)
        except Exception as e:
            print(f"Capture error at flip {target}: {e}", file=sys.stderr)
        _flip_capture_idx += 1
        if _flip_capture_idx >= len(frame_list):
            pyxel.quit()


pyxel.flip = _patched_flip

# Execute the user script
sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass
