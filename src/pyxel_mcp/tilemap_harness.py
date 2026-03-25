"""Tilemap inspection harness - dumps tilemap data as JSON.

Runs a Pyxel script and reads tilemap content at a target frame,
outputting tile grid, usage statistics, and bounding box.

Usage:
    python tilemap_harness.py <script> [tilemap_index] [target_frame]
"""

import json
import os
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

import pyxel

from pyxel_mcp._headless import patch_game_loop, run_script, setup_harness

setup_harness(script_path)

_captured = False


def _dump_tilemap():
    global _captured
    if _captured:
        return True
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
        "imgsrc": tm.imgsrc if isinstance(tm.imgsrc, int) else f"Image({tm.imgsrc.width}x{tm.imgsrc.height})",
        "bbox": bbox,
        "tiles": tiles,
        "tile_usage": dict(sorted(usage.items(), key=lambda x: -x[1])[:30]),
        "non_zero_tiles": non_zero,
        "total_scanned": scan_w * scan_h,
        "unique_tiles": len(usage),
    }

    print(json.dumps(result))
    sys.stdout.flush()
    return True


def _on_frame(fc, draw):
    if fc < target_frame:
        return False
    return _dump_tilemap()


patch_game_loop(_on_frame, on_show=lambda: _dump_tilemap())
run_script(script_path)
