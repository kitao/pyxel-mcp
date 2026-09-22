"""Tilemap analyzer."""

from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Any

import numpy as np

_TILES_GRID_LIMIT = 4096


def _resolve_imgsrc(tm) -> tuple[int | None, Any]:
    """Return the bank index (if any) and actual source Image.

    Image-valued sources may be standalone images. Pyxel also creates a fresh
    Python wrapper on each bank access, so compare native buffers when looking
    for a bank alias instead of comparing the wrappers' Python identities.
    """
    import pyxel

    val = tm.imgsrc
    if isinstance(val, int):
        return val, pyxel.images[val]
    address = ctypes.addressof(val.data_ptr())
    for i in range(len(pyxel.images)):
        if ctypes.addressof(pyxel.images[i].data_ptr()) == address:
            return i, val
    return None, val


def _zero_zero_is_visible(bank) -> bool:
    """Check if the (0,0) 8x8 tile in the source bank has any non-zero pixels."""
    bw, bh = bank.width, bank.height
    arr = np.frombuffer(
        bank.data_ptr(),
        dtype=np.uint8,
        count=bw * bh,
    ).reshape((bh, bw))
    return bool(np.any(arr[:8, :8] != 0))


def _render_tilemap_png(
    tilemap: int,
    bank,
    tm_w: int,
    tm_h: int,
    render_path: Path,
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
    import pyxel
    from PIL import Image as PILImage

    bw, bh = bank.width, bank.height
    bank_arr = np.frombuffer(
        bank.data_ptr(),
        dtype=np.uint8,
        count=bw * bh,
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
        tm.data_ptr(),
        dtype=np.uint16,
        count=tm.width * tm.height * 2,
    ).reshape((tm.height, tm.width, 2))

    for ty in range(tm_h):
        for tx in range(tm_w):
            u = int(tm_arr[ty, tx, 0])
            v = int(tm_arr[ty, tx, 1])
            # Preserve the in-bounds part of edge tiles in custom-sized Images.
            sy, sx = v * 8, u * 8
            if sy >= bh or sx >= bw:
                continue
            tile_h, tile_w = min(8, bh - sy), min(8, bw - sx)
            indices[ty * 8 : ty * 8 + tile_h, tx * 8 : tx * 8 + tile_w] = bank_arr[
                sy : sy + tile_h, sx : sx + tile_w
            ]

    rgb = lut[indices]  # (img_h, img_w, 3)

    render_path.parent.mkdir(parents=True, exist_ok=True)
    PILImage.fromarray(rgb, "RGB").save(render_path)


def analyze_tilemap(
    tilemap: int,
    *,
    render_path: str | None = None,
) -> dict[str, Any]:
    """Read tile coordinates, usage, bounds, and source-tile facts."""
    import pyxel

    tm = pyxel.tilemaps[tilemap]
    tm_w: int = tm.width
    tm_h: int = tm.height
    imgsrc, source_image = _resolve_imgsrc(tm)

    # Snapshot the tilemap as a (h, w, 2) uint16 array — Pyxel exposes the
    # tilemap memory as ushort pairs (u, v), little-endian on supported
    # platforms. `.copy()` once so subsequent script writes don't alias.
    tm_arr = (
        np.frombuffer(
            tm.data_ptr(),
            dtype=np.uint16,
            count=tm_w * tm_h * 2,
        )
        .reshape((tm_h, tm_w, 2))
        .copy()
    )

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

    zero_tile_nonempty = _zero_zero_is_visible(source_image)

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
        _render_tilemap_png(tilemap, source_image, render_w, render_h, rp)
        rendered = str(rp)

    return {
        "tilemap_index": tilemap,
        "size": [tm_w, tm_h],
        "imgsrc": imgsrc,
        "tiles": tiles,
        "usage": usage,
        "region": region,
        "zero_tile_used": uses_zero_zero,
        "zero_tile_nonempty": zero_tile_nonempty,
        "rendered": rendered,
        "errors": [],
    }
