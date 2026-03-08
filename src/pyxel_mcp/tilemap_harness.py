"""Tilemap inspection harness - dumps tilemap data as JSON.

Runs a Pyxel script and reads tilemap content at a target frame,
outputting tile grid, usage statistics, and bounding box.

Usage:
    python tilemap_harness.py <script> [tilemap_index] [target_frame]
"""

import json
import os
import runpy
import sys

if len(sys.argv) < 2:
    print(
        "Usage: tilemap_harness <script> [tilemap_index] [target_frame]",
        file=sys.stderr,
    )
    sys.exit(1)

script_path = os.path.abspath(sys.argv[1])
tilemap_index = int(sys.argv[2]) if len(sys.argv) > 2 else 0
target_frame = int(sys.argv[3]) if len(sys.argv) > 3 else 1

sys.argv = [script_path]

import pyxel

# Headless mode: no window, max speed
_original_init = pyxel.init


def _headless_init(*args, **kwargs):
    kwargs["headless"] = True
    _original_init(*args, **kwargs)
    os.chdir(os.path.dirname(script_path) or ".")


pyxel.init = _headless_init

_captured = False


def _dump_tilemap():
    global _captured
    if _captured:
        return
    _captured = True

    tm = pyxel.tilemaps[tilemap_index]
    w, h = tm.width, tm.height

    # Scan for bounding box of non-zero tiles and collect usage stats
    usage = {}
    min_x, min_y = w, h
    max_x, max_y = -1, -1
    scan_w = min(w, 256)
    scan_h = min(h, 256)

    for ty in range(scan_h):
        for tx in range(scan_w):
            tile = tm.pget(tx, ty)
            key = f"{tile[0]},{tile[1]}"
            usage[key] = usage.get(key, 0) + 1
            if tile != (0, 0):
                min_x = min(min_x, tx)
                min_y = min(min_y, ty)
                max_x = max(max_x, tx)
                max_y = max(max_y, ty)

    # Extract tile grid within bounding box (capped at 64x64)
    tiles = []
    bbox = None
    if max_x >= 0:
        bw = min(max_x - min_x + 1, 64)
        bh = min(max_y - min_y + 1, 64)
        for ty in range(min_y, min_y + bh):
            row = []
            for tx in range(min_x, min_x + bw):
                tile = tm.pget(tx, ty)
                row.append(list(tile))
            tiles.append(row)
        bbox = {"x": min_x, "y": min_y, "w": bw, "h": bh}

    non_zero = sum(v for k, v in usage.items() if k != "0,0")
    result = {
        "tilemap_index": tilemap_index,
        "width": w,
        "height": h,
        "imgsrc": tm.imgsrc,
        "bbox": bbox,
        "tiles": tiles,
        "tile_usage": dict(sorted(usage.items(), key=lambda x: -x[1])[:30]),
        "non_zero_tiles": non_zero,
        "total_scanned": scan_w * scan_h,
        "unique_tiles": len(usage),
    }

    print(json.dumps(result))
    sys.stdout.flush()
    pyxel.quit()


# Patch pyxel.run
_original_run = pyxel.run


def _patched_run(update, draw):
    def wrapped_update():
        update()
        if pyxel.frame_count >= target_frame:
            _dump_tilemap()

    _original_run(wrapped_update, draw)


pyxel.run = _patched_run

# Patch pyxel.show
_original_show = pyxel.show
pyxel.show = lambda: _dump_tilemap()

# Patch pyxel.flip
_flip_counter = 0
_original_flip = pyxel.flip


def _patched_flip():
    global _flip_counter
    _original_flip()
    _flip_counter += 1
    if _flip_counter >= target_frame:
        _dump_tilemap()


pyxel.flip = _patched_flip

# Execute
sys.path.insert(0, os.path.dirname(script_path))
try:
    runpy.run_path(script_path, run_name="__main__")
except SystemExit:
    pass
