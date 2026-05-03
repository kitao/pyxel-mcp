"""Palette analysis (spec §7.1)."""
from __future__ import annotations
from typing import Any

import numpy as np

# Pyxel default palette index ranges (heuristic per spec §7.1):
# - background: 0, 1, 5
# - environment: 3, 4, 13
# - interactive: 8, 10, 11
_DEFAULT_BACKGROUND = [0, 1, 5]
_DEFAULT_ENVIRONMENT = [3, 4, 13]
_DEFAULT_INTERACTIVE = [8, 10, 11]


def _hex(c: int) -> str:
    return f"#{c & 0xFFFFFF:06x}"


def _luminance(rgb: int) -> float:
    """WCAG relative luminance for an integer color 0xRRGGBB."""
    r = ((rgb >> 16) & 0xFF) / 255.0
    g = ((rgb >> 8) & 0xFF) / 255.0
    b = (rgb & 0xFF) / 255.0

    def _c(v: float) -> float:
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    return 0.2126 * _c(r) + 0.7152 * _c(g) + 0.0722 * _c(b)


def contrast_ratio(rgb_a: int, rgb_b: int) -> float:
    la, lb = _luminance(rgb_a), _luminance(rgb_b)
    lighter, darker = (la, lb) if la >= lb else (lb, la)
    return (lighter + 0.05) / (darker + 0.05)


def _hierarchy_score(used: set[int]) -> dict[str, Any]:
    """Score the 3-layer palette hierarchy from indices that were actually
    drawn into image banks.

    Pre-fix this counted layers based on `len(colors)` — i.e., the
    palette's *capacity* of 16 — which meant every default-palette game
    scored 2/2 regardless of which colours the script actually used.
    The intent of the check is "did the agent populate background,
    environment, and interactive bands?", which is only meaningful
    against `used_indices`.

    score: 2 = all three bands have at least one colour drawn; 1 = two
    bands; 0 = one or none.
    """
    bg_used = [i for i in _DEFAULT_BACKGROUND if i in used]
    env_used = [i for i in _DEFAULT_ENVIRONMENT if i in used]
    int_used = [i for i in _DEFAULT_INTERACTIVE if i in used]
    layers_present = sum(1 for layer in (bg_used, env_used, int_used) if layer)
    score = 2 if layers_present == 3 else (1 if layers_present == 2 else 0)
    return {
        "score": score,
        "background": bg_used,
        "environment": env_used,
        "interactive": int_used,
    }


def _scan_image_banks() -> tuple[set[int], set[tuple[int, int]]]:
    """Single-pass scan of all image banks: returns (used_indices, co_located_pairs).

    Implements spec §7.1's notion of "commonly co-located indices" at the
    pixel-data level: an unordered pair (i, j) is co-located iff some pixel
    with index i has a 4-neighbour pixel with index j (or vice versa) in any
    image bank. The transparent index 0 is excluded — pairings against the
    canvas don't represent on-screen contrast between rendered shapes.

    Vectorised via numpy on top of `pyxel.images[i].data_ptr()` — Pyxel exposes
    each bank as a contiguous (h, w) uint8 buffer of palette indices. We
    `.copy()` once per bank so subsequent script mutations don't leak into the
    snapshot, then derive used-indices from `np.unique` and co-located pairs
    from horizontal/vertical neighbour comparisons. Pre-fix this loop did
    ~200k Python pget calls per read_palette; post-fix it's 3 numpy passes.
    """
    import pyxel
    used: set[int] = set()
    pairs: set[tuple[int, int]] = set()
    for img in pyxel.images:
        w, h = img.width, img.height
        # Snapshot the bank to avoid aliasing if user code mutates it later.
        arr = np.frombuffer(
            img.data_ptr(), dtype=np.uint8, count=w * h,
        ).reshape((h, w)).copy()

        # used_indices: every non-zero unique value in the bank.
        uniq = np.unique(arr)
        for idx in uniq.tolist():
            if idx != 0:
                used.add(int(idx))

        # Co-located pairs via shifted comparisons:
        # - horizontal: arr[:, :-1] vs arr[:, 1:] (i.e., each pixel and its right neighbour)
        # - vertical:   arr[:-1, :] vs arr[1:, :] (each pixel and its down neighbour)
        # We keep both orientations because the original loop was directionally
        # biased (right + down) but the pair is order-invariant (sorted ascending).
        if w >= 2:
            a = arr[:, :-1].ravel()
            b = arr[:, 1:].ravel()
            mask = (a != 0) & (b != 0) & (a != b)
            if mask.any():
                ai = a[mask].astype(np.int32)
                bi = b[mask].astype(np.int32)
                lo = np.minimum(ai, bi)
                hi = np.maximum(ai, bi)
                # Encode pair as lo * 65536 + hi for cheap unique; both fit in 16 bits.
                packed = (lo.astype(np.int64) << 16) | hi.astype(np.int64)
                for v in np.unique(packed).tolist():
                    pairs.add((int(v >> 16), int(v & 0xFFFF)))
        if h >= 2:
            a = arr[:-1, :].ravel()
            b = arr[1:, :].ravel()
            mask = (a != 0) & (b != 0) & (a != b)
            if mask.any():
                ai = a[mask].astype(np.int32)
                bi = b[mask].astype(np.int32)
                lo = np.minimum(ai, bi)
                hi = np.maximum(ai, bi)
                packed = (lo.astype(np.int64) << 16) | hi.astype(np.int64)
                for v in np.unique(packed).tolist():
                    pairs.add((int(v >> 16), int(v & 0xFFFF)))
    return used, pairs


def _detect_close_pairs(
    colors: list[int],
    candidate_pairs: set[tuple[int, int]] | None = None,
) -> list[dict[str, Any]]:
    """Pairwise WCAG contrast; warn for ratio < 3.0 over candidate pairs.

    When `candidate_pairs` is provided (typically the co-located pair set
    from `_scan_image_banks`), only those pairs are evaluated — pairs that
    never appear adjacent on a sprite cannot create a real contrast issue.
    When None (legacy / extended-palette case), all index pairs are evaluated.
    """
    if candidate_pairs is None:
        pool = list(range(len(colors)))
        candidate_pairs = {(i, j) for i in pool for j in pool if i < j}
    out: list[dict[str, Any]] = []
    for i, j in sorted(candidate_pairs):
        if i >= len(colors) or j >= len(colors):
            continue
        r = contrast_ratio(colors[i], colors[j])
        if r < 3.0:
            out.append({
                "a": i,
                "b": j,
                "ratio": round(r, 2),
                "message": f"low contrast between palette {i} and {j}",
            })
    return out


def analyze_palette() -> dict[str, Any]:
    import pyxel
    colors = list(pyxel.colors)
    extended = len(colors) > 16
    used, co_located = _scan_image_banks()
    hierarchy = None if extended else _hierarchy_score(used)
    contrast_warnings = _detect_close_pairs(colors, co_located)
    info: dict[str, Any] = {
        "colors": {i: _hex(c) for i, c in enumerate(colors)},
        "extended_palette": extended,
        "palette_size": len(colors),
        "used_indices": sorted(used),
        "co_located_pairs": sorted(co_located),
        "hierarchy": hierarchy,
        "contrast_warnings": contrast_warnings,
        "errors": [],
    }
    return info
