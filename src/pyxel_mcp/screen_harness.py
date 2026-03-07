"""Screen pixel capture harness - captures screen as color index grid.

Runs a Pyxel script and at each target frame reads every screen pixel
with pyxel.pget(), outputting a JSON array of {frame, width, height, grid}.

Usage:
    python screen_harness.py <script> <frame_list_csv>
"""

import json
import os
import runpy
import sys

if len(sys.argv) < 3:
    print(
        "Usage: screen_harness <script> <frame_list_csv>",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
frame_list = sorted(set(max(1, int(f)) for f in sys.argv[2].split(",")))

sys.argv = [script_path]

import pyxel

# Turbo mode
_original_init = pyxel.init


def _turbo_init(*args, **kwargs):
    kwargs["fps"] = 10000
    _original_init(*args, **kwargs)
    os.chdir(os.path.dirname(script_path) or ".")


pyxel.init = _turbo_init

_results = []
_capture_idx = 0


def _read_screen():
    """Read all screen pixels as a 2D color index grid."""
    w, h = pyxel.width, pyxel.height
    grid = []
    for y in range(h):
        grid.append([pyxel.pget(x, y) for x in range(w)])
    return {"frame": pyxel.frame_count, "width": w, "height": h, "grid": grid}


def _flush_and_quit():
    print(json.dumps(_results))
    sys.stdout.flush()
    pyxel.quit()


def _try_capture(fc, draw):
    global _capture_idx
    if _capture_idx >= len(frame_list):
        return
    if fc >= frame_list[_capture_idx]:
        draw()
        _results.append(_read_screen())
        _capture_idx += 1
        if _capture_idx >= len(frame_list):
            _flush_and_quit()


# Patch pyxel.run
_original_run = pyxel.run


def _patched_run(update, draw):
    def wrapped_update():
        update()
        _try_capture(pyxel.frame_count, draw)

    _original_run(wrapped_update, draw)


pyxel.run = _patched_run

# Patch pyxel.show
_original_show = pyxel.show


def _patched_show():
    _results.append(_read_screen())
    _flush_and_quit()


pyxel.show = _patched_show

# Patch pyxel.flip
_flip_counter = 0
_original_flip = pyxel.flip


def _patched_flip():
    global _flip_counter, _capture_idx
    _original_flip()
    _flip_counter += 1
    if _capture_idx < len(frame_list) and _flip_counter >= frame_list[_capture_idx]:
        _results.append(_read_screen())
        _capture_idx += 1
        if _capture_idx >= len(frame_list):
            _flush_and_quit()


pyxel.flip = _patched_flip

# Execute
sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass
