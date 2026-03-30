"""State inspection harness - captures game object attributes at target frames.

Runs a Pyxel script, captures the App instance (the object that calls
pyxel.run()), and at each target frame dumps its attributes as JSON.

Supports single frame or comma-separated multi-frame timeline.

Usage:
    python state_harness.py <script> <frame_list> [attrs_json]
"""

import json
import os
import sys

if len(sys.argv) < 3:
    print(
        "Usage: state_harness <script> <frame_list> [attrs_json]",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
frame_list = sorted(set(max(1, int(f)) for f in sys.argv[2].split(",")))
filter_attrs = None
if len(sys.argv) > 3:
    filter_attrs = json.loads(sys.argv[3])

import pyxel

from pyxel_mcp._headless import run_script, setup_harness

setup_harness(script_path)

_app_instance = None
_results = []
_capture_idx = 0


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


def _capture_state():
    """Capture current state as a dict."""
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

    return result


def _flush_and_quit():
    # Output single object for one frame (backward compatible), array for multiple
    if len(frame_list) == 1:
        print("__PYXEL_MCP_JSON__:" + json.dumps(_results[0], default=str))
    else:
        print("__PYXEL_MCP_JSON__:" + json.dumps(_results, default=str))
    sys.stdout.flush()
    pyxel.quit()
    os._exit(0)


def _try_capture(fc):
    global _capture_idx
    if _capture_idx >= len(frame_list):
        return
    if fc >= frame_list[_capture_idx]:
        _results.append(_capture_state())
        _capture_idx += 1
        if _capture_idx >= len(frame_list):
            _flush_and_quit()


# Custom run/show/flip patches instead of patch_game_loop because we need
# to extract the App instance from update.__self__ / draw.__self__.
_original_run = pyxel.run


def _patched_run(update, draw):
    global _app_instance
    if hasattr(update, "__self__"):
        _app_instance = update.__self__
    elif hasattr(draw, "__self__"):
        _app_instance = draw.__self__

    def wrapped_update():
        update()
        _try_capture(pyxel.frame_count)

    _original_run(wrapped_update, draw)


pyxel.run = _patched_run

# Patch pyxel.show: dump state immediately
_original_show = pyxel.show


def _patched_show():
    _results.append(_capture_state())
    _flush_and_quit()


pyxel.show = _patched_show

# Patch pyxel.flip: use frame_count (Pyxel 2.8.9 advances it on flip)
_original_flip = pyxel.flip


def _patched_flip():
    _original_flip()
    _try_capture(pyxel.frame_count)


pyxel.flip = _patched_flip

# Execute the user script
run_script(script_path)
