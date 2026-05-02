"""Tilemap analyzer (spec §7.4)."""
from __future__ import annotations
from collections import Counter
from pathlib import Path
from typing import Any

_TILES_GRID_LIMIT = 4096


def _zero_zero_is_visible(imgsrc: int) -> bool:
    """Check if the (0,0) 8x8 tile in the source bank has any non-zero pixels."""
    import pyxel
    bank = pyxel.images[imgsrc]
    for yy in range(8):
        for xx in range(8):
            if bank.pget(xx, yy) != 0:
                return True
    return False


def _render_tilemap_png(
    tilemap: int, imgsrc: int, tm_w: int, tm_h: int, render_path: Path,
) -> None:
    """Render visible tilemap region to a PNG using PIL."""
    from PIL import Image as PILImage
    import pyxel

    bank = pyxel.images[imgsrc]
    palette_rgb = []
    for c in pyxel.colors:
        palette_rgb.append(((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF))

    img_w = tm_w * 8
    img_h = tm_h * 8
    import numpy as np
    rgb = np.zeros((img_h, img_w, 3), dtype=np.uint8)

    tm = pyxel.tilemaps[tilemap]
    for ty in range(tm_h):
        for tx in range(tm_w):
            u, v = tm.pget(tx, ty)
            for py in range(8):
                for px in range(8):
                    ci = bank.pget(u * 8 + px, v * 8 + py)
                    r, g, b = palette_rgb[ci]
                    rgb[ty * 8 + py, tx * 8 + px] = (r, g, b)

    render_path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(rgb, "RGB").save(render_path)


def analyze_tilemap(
    tilemap: int,
    *,
    render_path: str | None = None,
) -> dict[str, Any]:
    """Analyze a Pyxel tilemap: usage, bounding_box, trap_warning."""
    import pyxel

    tm = pyxel.tilemaps[tilemap]
    tm_w: int = tm.width
    tm_h: int = tm.height
    imgsrc: int = int(getattr(tm, "imgsrc", 0))

    # Count tile usage via pget iteration
    counter: Counter[str] = Counter()
    uses_zero_zero = False

    min_x = tm_w
    min_y = tm_h
    max_x = -1
    max_y = -1

    for ty in range(tm_h):
        for tx in range(tm_w):
            u, v = tm.pget(tx, ty)
            key = f"{u},{v}"
            counter[key] += 1
            if u == 0 and v == 0:
                uses_zero_zero = True
            else:
                # Track bounding box of non-(0,0) tiles
                if tx < min_x:
                    min_x = tx
                if tx > max_x:
                    max_x = tx
                if ty < min_y:
                    min_y = ty
                if ty > max_y:
                    max_y = ty

    # Remove (0,0) from usage — it is implicitly everywhere (background/empty)
    usage = {k: v for k, v in counter.items() if k != "0,0"}

    # Bounding box covers non-(0,0) tiles only
    if max_x >= 0:
        bounding_box: dict[str, int] | None = {
            "x": min_x,
            "y": min_y,
            "w": max_x - min_x + 1,
            "h": max_y - min_y + 1,
        }
    else:
        bounding_box = None

    # trap_warning: (0,0) tile appears in usage AND source bank (0,0) has visible content
    trap_warning = uses_zero_zero and _zero_zero_is_visible(imgsrc)

    # tiles: full grid only when small enough
    total_cells = tm_w * tm_h
    if total_cells <= _TILES_GRID_LIMIT:
        tiles: list[list[list[int]]] | None = [
            [list(tm.pget(tx, ty)) for tx in range(tm_w)]
            for ty in range(tm_h)
        ]
    else:
        tiles = None

    rendered = None
    if render_path:
        rp = Path(render_path).resolve()
        # Limit render to bounding box region (or full tilemap if small)
        if bounding_box is not None:
            render_w = bounding_box["x"] + bounding_box["w"]
            render_h = bounding_box["y"] + bounding_box["h"]
            render_w = min(render_w, tm_w)
            render_h = min(render_h, tm_h)
        else:
            render_w = min(tm_w, 64)
            render_h = min(tm_h, 64)
        _render_tilemap_png(tilemap, imgsrc, render_w, render_h, rp)
        rendered = str(rp)

    return {
        "tilemap_index": tilemap,
        "size": [tm_w, tm_h],
        "imgsrc": imgsrc,
        "tiles": tiles,
        "usage": usage,
        "bounding_box": bounding_box,
        "trap_warning": trap_warning,
        "rendered": rendered,
        "warnings": [],
        "errors": [],
    }
