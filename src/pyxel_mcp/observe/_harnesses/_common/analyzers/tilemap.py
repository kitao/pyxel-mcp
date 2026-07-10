"""Tilemap analyzer."""
from __future__ import annotations
from pathlib import Path
from typing import Any

import numpy as np

_TILES_GRID_LIMIT = 4096


def _resolve_imgsrc(tm) -> int:
    """Return the source-bank index of a tilemap.

    Pyxel exposes the source bank as `tm.imgsrc` (int). If user code did
    `tm.image = pyxel.images[N]` (legacy shortcut), `imgsrc` becomes an
    Image object, not an int — the naive `int(getattr(tm, "imgsrc", 0))`
    raises TypeError. Identity-scan over `pyxel.images` to recover the
    index in that case; default to 0 for any other surprise.
    """
    import pyxel
    val = getattr(tm, "imgsrc", 0)
    if isinstance(val, int):
        return val
    # imgsrc may be an Image instance (after `tm.image = pyxel.images[N]`).
    for i in range(len(pyxel.images)):
        if pyxel.images[i] is val:
            return i
    return 0


def _zero_zero_is_visible(imgsrc: int) -> bool:
    """Check if the (0,0) 8x8 tile in the source bank has any non-zero pixels."""
    import pyxel
    bank = pyxel.images[imgsrc]
    bw, bh = bank.width, bank.height
    arr = np.frombuffer(
        bank.data_ptr(), dtype=np.uint8, count=bw * bh,
    ).reshape((bh, bw))
    return bool(np.any(arr[:8, :8] != 0))


def _render_tilemap_png(
    tilemap: int, imgsrc: int, tm_w: int, tm_h: int, render_path: Path,
) -> None:
    """Render visible tilemap region to a PNG using PIL.

    Vectorised pipeline:
      1. Snapshot the source bank as a (bh, bw) uint8 numpy array.
      2. Build a (256, 3) palette LUT once.
      3. Read tilemap (u, v) coords for the visible region from data_ptr().
      4. For each cell, slice the corresponding 8x8 tile out of the bank
         and place it into the indices buffer; convert to RGB at the end
         via a single LUT lookup.
    """
    from PIL import Image as PILImage
    import pyxel

    bank = pyxel.images[imgsrc]
    bw, bh = bank.width, bank.height
    bank_arr = np.frombuffer(
        bank.data_ptr(), dtype=np.uint8, count=bw * bh,
    ).reshape((bh, bw))

    # Palette LUT: index → (r, g, b). Pad to 256 to allow direct indexing.
    lut = np.zeros((256, 3), dtype=np.uint8)
    for i, c in enumerate(pyxel.colors):
        lut[i, 0] = (c >> 16) & 0xFF
        lut[i, 1] = (c >> 8) & 0xFF
        lut[i, 2] = c & 0xFF

    img_w = tm_w * 8
    img_h = tm_h * 8
    indices = np.zeros((img_h, img_w), dtype=np.uint8)

    tm = pyxel.tilemaps[tilemap]
    tm_arr = np.frombuffer(
        tm.data_ptr(), dtype=np.uint16, count=tm.width * tm.height * 2,
    ).reshape((tm.height, tm.width, 2))

    for ty in range(tm_h):
        for tx in range(tm_w):
            u = int(tm_arr[ty, tx, 0])
            v = int(tm_arr[ty, tx, 1])
            # Clamp source slice to bank bounds; out-of-range tiles render as 0.
            sy, sx = v * 8, u * 8
            if sy + 8 > bh or sx + 8 > bw or sy < 0 or sx < 0:
                continue
            indices[ty * 8:ty * 8 + 8, tx * 8:tx * 8 + 8] = bank_arr[sy:sy + 8, sx:sx + 8]

    rgb = lut[indices]  # (img_h, img_w, 3)

    render_path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(rgb, "RGB").save(render_path)


def analyze_tilemap(
    tilemap: int,
    *,
    render_path: str | None = None,
) -> dict[str, Any]:
    """Analyze a Pyxel tilemap: usage, region, trap_warning."""
    import pyxel

    tm = pyxel.tilemaps[tilemap]
    tm_w: int = tm.width
    tm_h: int = tm.height
    imgsrc = _resolve_imgsrc(tm)

    # Snapshot the tilemap as a (h, w, 2) uint16 array — Pyxel exposes the
    # tilemap memory as ushort pairs (u, v), little-endian on supported
    # platforms. `.copy()` once so subsequent script writes don't alias.
    tm_arr = np.frombuffer(
        tm.data_ptr(), dtype=np.uint16, count=tm_w * tm_h * 2,
    ).reshape((tm_h, tm_w, 2)).copy()

    # Detect (0,0) tile presence and non-(0,0) bounding box.
    is_zero = (tm_arr[..., 0] == 0) & (tm_arr[..., 1] == 0)
    uses_zero_zero = bool(np.any(is_zero))

    nonzero_mask = ~is_zero
    if np.any(nonzero_mask):
        ys, xs = np.where(nonzero_mask)
        min_x, max_x = int(xs.min()), int(xs.max())
        min_y, max_y = int(ys.min()), int(ys.max())
        region: dict[str, int] | None = {
            "x": min_x,
            "y": min_y,
            "w": max_x - min_x + 1,
            "h": max_y - min_y + 1,
        }
    else:
        region = None

    # Build usage dict keyed by "u,v" — exclude (0,0) since it's the
    # implicit background / empty tile.
    # Pack (u, v) into a single uint32 for unique counting, then unpack.
    packed = (tm_arr[..., 0].astype(np.uint32) << 16) | tm_arr[..., 1].astype(np.uint32)
    pkeys, pcounts = np.unique(packed, return_counts=True)
    usage: dict[str, int] = {}
    for k, c in zip(pkeys.tolist(), pcounts.tolist()):
        u = (k >> 16) & 0xFFFF
        v = k & 0xFFFF
        if u == 0 and v == 0:
            continue
        usage[f"{u},{v}"] = int(c)

    # trap_warning: (0,0) tile appears in usage AND source bank (0,0) has visible content
    trap_warning = uses_zero_zero and _zero_zero_is_visible(imgsrc)

    # tiles: full grid only when small enough — return as nested int lists.
    total_cells = tm_w * tm_h
    if total_cells <= _TILES_GRID_LIMIT:
        tiles: list[list[list[int]]] | None = tm_arr.astype(int).tolist()
    else:
        tiles = None

    rendered = None
    if render_path:
        rp = Path(render_path).resolve()
        # Limit render to bounding region (or full tilemap if small)
        if region is not None:
            render_w = region["x"] + region["w"]
            render_h = region["y"] + region["h"]
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
        "region": region,
        "trap_warning": trap_warning,
        "rendered": rendered,
        "warnings": [],
        "errors": [],
    }
