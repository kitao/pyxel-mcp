"""Input simulation harness - simulates key/mouse input and captures screenshots.

Runs a Pyxel script with simulated input events at specified frames and saves
screenshots at each capture frame.

Usage:
    python input_harness.py <script> <output_dir> <capture_csv> <scale> <input_file>
"""

import json
import os
import runpy
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

sys.argv = [script_path]

with open(input_file) as f:
    input_schedule = sorted(json.load(f), key=lambda e: e["frame"])

import pyxel

# --- Input simulation state ---

_prev_keys = set()
_curr_keys = set()
_schedule_idx = 0
_last_keys = set()
_last_mouse_x = 0
_last_mouse_y = 0


def _resolve_key(name):
    """Convert key name like 'KEY_SPACE' to pyxel constant."""
    val = getattr(pyxel, name, None)
    if val is None:
        raise ValueError(f"Unknown key: {name}")
    return val


def _update_input_state():
    """Advance input state to match current frame_count."""
    global _prev_keys, _curr_keys, _schedule_idx
    global _last_keys, _last_mouse_x, _last_mouse_y

    _prev_keys = _curr_keys.copy()
    fc = pyxel.frame_count

    while _schedule_idx < len(input_schedule):
        entry = input_schedule[_schedule_idx]
        if entry["frame"] > fc:
            break
        _last_keys = set(_resolve_key(k) for k in entry.get("keys", []))
        if "mouse_x" in entry:
            _last_mouse_x = entry["mouse_x"]
        if "mouse_y" in entry:
            _last_mouse_y = entry["mouse_y"]
        _schedule_idx += 1

    _curr_keys = _last_keys.copy()
    pyxel.mouse_x = _last_mouse_x
    pyxel.mouse_y = _last_mouse_y


# Patch input functions


def _sim_btn(key):
    return key in _curr_keys


def _sim_btnp(key, hold=None, repeat=None):
    return key in _curr_keys and key not in _prev_keys


def _sim_btnr(key):
    return key not in _curr_keys and key in _prev_keys


pyxel.btn = _sim_btn
pyxel.btnp = _sim_btnp
pyxel.btnr = _sim_btnr

# --- Turbo mode ---

_original_init = pyxel.init


def _turbo_init(*args, **kwargs):
    kwargs["fps"] = 10000
    _original_init(*args, **kwargs)
    os.chdir(os.path.dirname(script_path) or ".")


pyxel.init = _turbo_init

# --- Frame capture (in update to avoid turbo-mode draw skipping) ---

_capture_idx = 0


def _try_capture(fc, draw):
    """Capture at the current frame if it matches the next target."""
    global _capture_idx
    if _capture_idx >= len(frame_list):
        return
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


# Patch pyxel.run: wrap update for input simulation + capture
_original_run = pyxel.run


def _patched_run(update, draw):
    def wrapped_update():
        _update_input_state()
        update()
        _try_capture(pyxel.frame_count, draw)

    _original_run(wrapped_update, draw)


pyxel.run = _patched_run

# Patch pyxel.show: capture as static image
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
    _update_input_state()
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
