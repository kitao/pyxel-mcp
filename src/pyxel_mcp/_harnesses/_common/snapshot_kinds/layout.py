"""layout snapshot — balance analysis (spec §6.4.4)."""
from __future__ import annotations
from typing import Any

import numpy as np


def _read_screen() -> tuple[np.ndarray, int, int]:
    import pyxel
    w, h = pyxel.width, pyxel.height
    arr = np.array(
        [[pyxel.screen.pget(x, y) for x in range(w)] for y in range(h)],
        dtype=np.uint8,
    )
    return arr, w, h


def _density_mask(arr: np.ndarray) -> np.ndarray:
    """Pixels considered 'content' (non-background palette index 0)."""
    return arr != 0


def _h_balance(mask: np.ndarray) -> float:
    h, w = mask.shape
    left = mask[:, : w // 2].sum()
    right = mask[:, w // 2 :].sum()
    total = left + right
    if total == 0:
        return 1.0
    return 1.0 - abs(int(left) - int(right)) / int(total)


def _v_balance(mask: np.ndarray) -> float:
    h, w = mask.shape
    top = mask[: h // 2, :].sum()
    bottom = mask[h // 2 :, :].sum()
    total = top + bottom
    if total == 0:
        return 1.0
    return 1.0 - abs(int(top) - int(bottom)) / int(total)


def _quadrant_density(mask: np.ndarray) -> list[float]:
    h, w = mask.shape
    total = mask.sum()
    if total == 0:
        return [0.0, 0.0, 0.0, 0.0]
    tl = mask[: h // 2, : w // 2].sum()
    tr = mask[: h // 2, w // 2 :].sum()
    bl = mask[h // 2 :, : w // 2].sum()
    br = mask[h // 2 :, w // 2 :].sum()
    return [
        float(tl) / float(total),
        float(tr) / float(total),
        float(bl) / float(total),
        float(br) / float(total),
    ]


def _center_of_mass(mask: np.ndarray) -> list[float]:
    if not mask.any():
        h, w = mask.shape
        return [w / 2.0, h / 2.0]
    ys, xs = np.where(mask)
    return [float(xs.mean()), float(ys.mean())]


def _detect_text_positions(arr: np.ndarray) -> list[dict[str, Any]]:
    """Heuristic text-block detection. Deferred to a future task."""
    return []


def capture(snapshot: dict[str, Any]) -> dict[str, Any]:
    arr, w, h = _read_screen()
    mask = _density_mask(arr)
    return {
        "frame": snapshot["frame"],
        "kind": "layout",
        "h_balance": _h_balance(mask),
        "v_balance": _v_balance(mask),
        "quadrant_density": _quadrant_density(mask),
        "center_of_mass": _center_of_mass(mask),
        "text_positions": _detect_text_positions(arr),
        "warnings": [],
    }
