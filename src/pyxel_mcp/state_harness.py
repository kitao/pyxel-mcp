"""State inspection harness - captures game object attributes at a target frame.

Runs a Pyxel script, captures the App instance (the object that calls
pyxel.run()), and at the target frame dumps its attributes as JSON.

Usage:
    python state_harness.py <script> <target_frame> [attrs_json]
"""

import json
import os
import runpy
import sys

if len(sys.argv) < 3:
    print(
        "Usage: state_harness <script> <target_frame> [attrs_json]",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
target_frame = int(sys.argv[2])
filter_attrs = None
if len(sys.argv) > 3:
    filter_attrs = json.loads(sys.argv[3])

sys.argv = [script_path]

import pyxel

# Turbo mode
_original_init = pyxel.init


def _turbo_init(*args, **kwargs):
    kwargs["fps"] = 10000
    _original_init(*args, **kwargs)
    os.chdir(os.path.dirname(script_path) or ".")


pyxel.init = _turbo_init

_app_instance = None
_captured = False


def _safe_serialize(obj, depth=0, max_depth=3):
    """Serialize an object to JSON-safe form with depth limit."""
    if depth > max_depth:
        return f"<{type(obj).__name__}>"
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    if isinstance(obj, (list, tuple)):
        items = [_safe_serialize(item, depth + 1, max_depth) for item in obj[:100]]
        if len(obj) > 100:
            items.append(f"... ({len(obj)} total)")
        return items
    if isinstance(obj, dict):
        result = {}
        for k, v in list(obj.items())[:100]:
            result[str(k)] = _safe_serialize(v, depth + 1, max_depth)
        if len(obj) > 100:
            result["..."] = f"({len(obj)} total)"
        return result
    if isinstance(obj, set):
        sortable = all(isinstance(x, (int, float, str)) for x in obj)
        return _safe_serialize(sorted(obj) if sortable else list(obj), depth, max_depth)
    if callable(obj):
        return f"<function {getattr(obj, '__name__', '?')}>"
    if hasattr(obj, "__dict__"):
        attrs = {
            k: _safe_serialize(v, depth + 1, max_depth)
            for k, v in list(vars(obj).items())[:50]
            if not k.startswith("_")
        }
        attrs["__type__"] = type(obj).__name__
        return attrs
    return f"<{type(obj).__name__}>"


def _dump_state():
    """Dump the captured app instance state as JSON."""
    global _captured
    if _captured:
        return
    _captured = True

    result = {"frame": pyxel.frame_count}
    result["pyxel"] = {
        "width": pyxel.width,
        "height": pyxel.height,
    }

    if _app_instance is not None:
        attrs = vars(_app_instance)
        if filter_attrs:
            attrs = {k: v for k, v in attrs.items() if k in filter_attrs}
        else:
            attrs = {k: v for k, v in attrs.items() if not k.startswith("_")}
        result["app_type"] = type(_app_instance).__name__
        result["attributes"] = {
            k: _safe_serialize(v) for k, v in attrs.items()
        }
    else:
        result["app_type"] = None
        result["note"] = "No App instance found (pyxel.run() not called with bound method)"

    print(json.dumps(result, default=str))
    sys.stdout.flush()
    pyxel.quit()


# Patch pyxel.run: capture self from bound methods, dump at target frame
_original_run = pyxel.run


def _patched_run(update, draw):
    global _app_instance
    if hasattr(update, "__self__"):
        _app_instance = update.__self__
    elif hasattr(draw, "__self__"):
        _app_instance = draw.__self__

    def wrapped_update():
        update()
        if pyxel.frame_count >= target_frame:
            _dump_state()

    _original_run(wrapped_update, draw)


pyxel.run = _patched_run

# Patch pyxel.show: dump state immediately
_original_show = pyxel.show


def _patched_show():
    _dump_state()


pyxel.show = _patched_show

# Patch pyxel.flip: count flips and dump at target
_flip_counter = 0
_original_flip = pyxel.flip


def _patched_flip():
    global _flip_counter
    _original_flip()
    _flip_counter += 1
    if _flip_counter >= target_frame:
        _dump_state()


pyxel.flip = _patched_flip

# Execute the user script
sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass
