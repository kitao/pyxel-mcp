"""Tilemap analyzer."""

from __future__ import annotations

import ctypes
from pathlib import Path
from typing import Any

import numpy as np

from pyxel_mcp.observe._harnesses._common.pixels import rgb_image

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
    tiles: np.ndarray,
    bank,
    render_path: Path,
) -> None:
    """Render the selected tiles, clipping partial tiles from custom images."""
    bw, bh = bank.width, bank.height
    bank_arr = np.frombuffer(
        bank.data_ptr(),
        dtype=np.uint8,
        count=bw * bh,
    ).reshape((bh, bw))

    tm_h, tm_w = tiles.shape[:2]
    indices = np.zeros((tm_h * 8, tm_w * 8), dtype=np.uint8)
    for ty in range(tm_h):
        for tx in range(tm_w):
            u = int(tiles[ty, tx, 0])
            v = int(tiles[ty, tx, 1])
            # Preserve the in-bounds part of edge tiles in custom-sized Images.
            sy, sx = v * 8, u * 8
            if sy >= bh or sx >= bw:
                continue
            tile_h, tile_w = min(8, bh - sy), min(8, bw - sx)
            indices[ty * 8 : ty * 8 + tile_h, tx * 8 : tx * 8 + tile_w] = bank_arr[
                sy : sy + tile_h, sx : sx + tile_w
            ]

    render_path.parent.mkdir(parents=True, exist_ok=True)
    rgb_image(indices).save(render_path, format="PNG")


def analyze_tilemap(
    tilemap: int,
    *,
    render_path: str | None = None,
    bbox: tuple[int, int, int, int] | None = None,
) -> dict[str, Any]:
    """Read tile coordinates, usage, bounds, and source-tile facts."""
    import pyxel

    tm = pyxel.tilemaps[tilemap]
    tm_w: int = tm.width
    tm_h: int = tm.height
    imgsrc, source_image = _resolve_imgsrc(tm)

    x, y, w, h = bbox if bbox is not None else (0, 0, tm_w, tm_h)
    tm_arr = np.frombuffer(tm.data_ptr(), dtype=np.uint16).reshape(tm_h, tm_w, 2)[
        y : y + h, x : x + w
    ]
    h, w = tm_arr.shape[:2]

    # Detect (0,0) tile presence and non-(0,0) bounding box.
    is_zero = (tm_arr[..., 0] == 0) & (tm_arr[..., 1] == 0)
    uses_zero_zero = bool(np.any(is_zero))

    nonzero_mask = ~is_zero
    if np.any(nonzero_mask):
        ys, xs = np.where(nonzero_mask)
        min_x, max_x = int(xs.min()), int(xs.max())
        min_y, max_y = int(ys.min()), int(ys.max())
        region: dict[str, int] | None = {
            "x": x + min_x,
            "y": y + min_y,
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
    total_cells = w * h
    if total_cells <= _TILES_GRID_LIMIT:
        tiles: list[list[list[int]]] | None = tm_arr.astype(int).tolist()
    else:
        tiles = None

    rendered = None
    if render_path:
        rp = Path(render_path).resolve()
        render_tiles = tm_arr
        if bbox is None:
            # Keep the historical overview from the origin to the last used tile.
            render_w = region["x"] + region["w"] if region else 64
            render_h = region["y"] + region["h"] if region else 64
            render_tiles = tm_arr[:render_h, :render_w]
        _render_tilemap_png(render_tiles, source_image, rp)
        rendered = str(rp)

    return {
        "tilemap_index": tilemap,
        "size": [tm_w, tm_h],
        "imgsrc": imgsrc,
        "tiles": tiles,
        "sampled_region": {"x": x, "y": y, "w": w, "h": h},
        "usage": usage,
        "region": region,
        "zero_tile_used": uses_zero_zero,
        "zero_tile_nonempty": zero_tile_nonempty,
        "rendered": rendered,
        "errors": [],
    }
