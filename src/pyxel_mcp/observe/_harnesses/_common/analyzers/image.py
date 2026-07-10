"""Image bank region analyzer."""
from __future__ import annotations
from pathlib import Path
from typing import Any

import numpy as np

_PIXEL_GRID_LIMIT = 4096


def _bank_size(image: int) -> tuple[int, int]:
    import pyxel
    bank = pyxel.images[image]
    return bank.width, bank.height


def _read_region(image: int, x: int, y: int, w: int, h: int) -> np.ndarray:
    """Read a region from an image bank via numpy slicing on data_ptr().

    Pyxel exposes each bank as a contiguous (h, w) uint8 buffer of palette
    indices. We `.copy()` the slice so subsequent script writes don't leak
    into this snapshot (data_ptr aliases live memory).
    """
    import pyxel
    bank = pyxel.images[image]
    bw, bh = bank.width, bank.height
    full = np.frombuffer(
        bank.data_ptr(), dtype=np.uint8, count=bw * bh,
    ).reshape((bh, bw))
    return full[y:y + h, x:x + w].copy()


def _color_count(region: np.ndarray) -> dict[int, int]:
    if region.size == 0:
        return {}
    vals, counts = np.unique(region, return_counts=True)
    return {int(v): int(c) for v, c in zip(vals.tolist(), counts.tolist())}


def _fill_ratio(region: np.ndarray) -> float:
    if region.size == 0:
        return 0.0
    nonzero = (region != 0).sum()
    return float(nonzero) / float(region.size)


def _symmetry(region: np.ndarray) -> dict[str, float]:
    if region.size == 0:
        return {"horizontal": 1.0, "vertical": 1.0}
    h_match = (region == region[:, ::-1]).mean()
    v_match = (region == region[::-1, :]).mean()
    return {"horizontal": float(h_match), "vertical": float(v_match)}


def _edge_density(region: np.ndarray) -> float:
    if region.size == 0:
        return 0.0
    perim = np.concatenate([region[0, :], region[-1, :], region[:, 0], region[:, -1]])
    return float((perim != 0).sum()) / float(perim.size)


def _render_png(region: np.ndarray, render_path: Path) -> None:
    from PIL import Image
    import pyxel
    palette_rgb = []
    for c in pyxel.colors:
        palette_rgb.append(((c >> 16) & 0xFF, (c >> 8) & 0xFF, c & 0xFF))
    h, w = region.shape
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    for idx, (r, g, b) in enumerate(palette_rgb):
        mask = region == idx
        rgb[mask] = (r, g, b)
    render_path.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgb, "RGB").save(render_path)


def analyze_image(
    image: int,
    x: int = 0,
    y: int = 0,
    w: int | None = None,
    h: int | None = None,
    render_path: str | None = None,
) -> dict[str, Any]:
    bank_w, bank_h = _bank_size(image)
    warnings: list[str] = []
    rx, ry = max(0, x), max(0, y)
    rw = bank_w - rx if w is None else w
    rh = bank_h - ry if h is None else h
    if rx + rw > bank_w or ry + rh > bank_h:
        new_rw = min(rw, bank_w - rx)
        new_rh = min(rh, bank_h - ry)
        warnings.append(f"region clamped from ({rw}x{rh}) to ({new_rw}x{new_rh})")
        rw, rh = new_rw, new_rh

    region = _read_region(image, rx, ry, rw, rh)
    area = rw * rh
    pixels = region.tolist() if area <= _PIXEL_GRID_LIMIT else None
    color_count = _color_count(region)
    fill = _fill_ratio(region)

    if 0 < area <= _PIXEL_GRID_LIMIT:
        sym = _symmetry(region)
        edge = _edge_density(region)
    else:
        sym = None
        edge = None

    if not (0.15 <= fill <= 0.95):
        warnings.append(f"fill_ratio {fill:.2f} outside expected [0.15, 0.95]")

    rendered = None
    if render_path:
        rp = Path(render_path).resolve()
        _render_png(region, rp)
        rendered = str(rp)

    return {
        "image_index": image,
        "bank_size": [bank_w, bank_h],
        "region": {"x": rx, "y": ry, "w": rw, "h": rh},
        "pixels": pixels,
        "color_count": color_count,
        "fill_ratio": fill,
        "symmetry": sym,
        "edge_density": edge,
        "warnings": warnings,
        "rendered": rendered,
        "errors": [],
    }
