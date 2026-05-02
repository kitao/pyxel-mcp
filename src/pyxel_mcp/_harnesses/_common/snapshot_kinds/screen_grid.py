"""screen_grid snapshot — palette indices as 2D array (spec §6.4.2)."""
from __future__ import annotations
from typing import Any

import numpy as np


def capture(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return the screen as a 2D array of palette indices (0-15).

    Reads pyxel.screen.data_ptr() into a numpy array and slices the bbox.
    Optional ``bbox`` restricts the region; values extending past the
    screen edge are clamped and a warning is appended to the result.
    """
    import pyxel
    sw, sh = pyxel.width, pyxel.height
    warnings: list[str] = []

    bbox = snapshot.get("bbox")
    if bbox is None:
        x, y, w, h = 0, 0, sw, sh
    else:
        x, y, w, h = bbox
        cx = max(0, x)
        cy = max(0, y)
        cw = min(w, sw - cx)
        ch = min(h, sh - cy)
        if (cx, cy, cw, ch) != (x, y, w, h):
            warnings.append(f"bbox clamped from {bbox} to [{cx}, {cy}, {cw}, {ch}]")
        x, y, w, h = cx, cy, cw, ch

    arr = np.frombuffer(
        pyxel.screen.data_ptr(), dtype=np.uint8, count=sw * sh,
    ).reshape((sh, sw))
    grid = arr[y:y + h, x:x + w].astype(int).tolist()
    return {
        "frame": snapshot["frame"],
        "kind": "screen_grid",
        "bbox": [x, y, w, h],
        "grid": grid,
        "warnings": warnings,
    }
