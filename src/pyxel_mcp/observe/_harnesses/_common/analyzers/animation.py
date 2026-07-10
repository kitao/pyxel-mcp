"""Animation strip analyzer."""
from __future__ import annotations
from typing import Any

import numpy as np


def _bank_size(image: int) -> tuple[int, int]:
    import pyxel
    bank = pyxel.images[image]
    return bank.width, bank.height


def _bank_array(bank) -> np.ndarray:
    """Return the entire bank as a (h, w) uint8 numpy snapshot.

    `.copy()` once so subsequent script writes don't alias into our regions.
    """
    bw, bh = bank.width, bank.height
    return np.frombuffer(
        bank.data_ptr(), dtype=np.uint8, count=bw * bh,
    ).reshape((bh, bw)).copy()


def _read_region(bank_arr: np.ndarray, x: int, y: int, w: int, h: int) -> np.ndarray:
    """Slice a w x h region from a pre-snapshotted bank array."""
    return bank_arr[y:y + h, x:x + w]


def _palette_jaccard(regions: list[np.ndarray]) -> float:
    """Jaccard similarity of color index sets across all regions."""
    if not regions:
        return 1.0
    palette_sets = [set(np.unique(r).tolist()) for r in regions]
    inter = palette_sets[0].copy()
    union = palette_sets[0].copy()
    for s in palette_sets[1:]:
        inter &= s
        union |= s
    if not union:
        return 1.0
    return len(inter) / len(union)


def _silhouette_jaccard(a: np.ndarray, b: np.ndarray) -> float:
    """Jaccard of fill masks (palette index 0 = background)."""
    ma = (a != 0)
    mb = (b != 0)
    union = (ma | mb).sum()
    if union == 0:
        return 1.0
    inter = (ma & mb).sum()
    return float(inter) / float(union)


def analyze_animation(
    *, image: int, x: int, y: int, w: int, h: int,
    region_count: int, direction: str,
) -> dict[str, Any]:
    if region_count < 2:
        raise ValueError("region_count must be >= 2")
    if direction not in ("horizontal", "vertical"):
        raise ValueError(f"direction must be 'horizontal' or 'vertical', got {direction!r}")

    bank_w, bank_h = _bank_size(image)

    import pyxel
    bank = pyxel.images[image]
    bank_arr = _bank_array(bank)

    regions: list[np.ndarray] = []
    region_meta: list[dict[str, Any]] = []

    for i in range(region_count):
        rx = x + (i * w if direction == "horizontal" else 0)
        ry = y + (i * h if direction == "vertical" else 0)
        if rx + w > bank_w or ry + h > bank_h:
            raise ValueError(
                f"region {i} at ({rx},{ry}) ({w}x{h}) overflows bank {bank_w}x{bank_h}"
            )
        region = _read_region(bank_arr, rx, ry, w, h)
        regions.append(region)
        vals, counts = np.unique(region, return_counts=True)
        cc = {int(v): int(c) for v, c in zip(vals.tolist(), counts.tolist())}
        fill = float((region != 0).sum()) / float(region.size) if region.size else 0.0
        region_meta.append({
            "region": {"x": rx, "y": ry, "w": w, "h": h},
            "color_count": cc,
            "fill_ratio": fill,
        })

    pal_consistency = _palette_jaccard(regions)
    sil_pairs = [
        _silhouette_jaccard(regions[i], regions[i + 1])
        for i in range(region_count - 1)
    ]
    silhouette_stability = sum(sil_pairs) / len(sil_pairs) if sil_pairs else 1.0

    # Vectorised pairwise XOR-style diff. Shape-equal regions guaranteed by
    # the overflow check above, so we can stack them and compare in one op.
    region_diffs: list[dict[str, Any]] = []
    if region_count >= 2:
        stacked = np.stack(regions)  # (region_count, h, w)
        diffs = np.count_nonzero(stacked[:-1] != stacked[1:], axis=(1, 2))
        denom = float(w * h)
        for i, diff in enumerate(diffs.tolist()):
            region_diffs.append({
                "from": i,
                "to": i + 1,
                "diff_ratio": float(diff) / denom,
            })

    return {
        "image_index": image,
        "regions": region_meta,
        "palette_consistency": pal_consistency,
        "silhouette_stability": silhouette_stability,
        "region_diffs": region_diffs,
        "warnings": [],
        "errors": [],
    }
