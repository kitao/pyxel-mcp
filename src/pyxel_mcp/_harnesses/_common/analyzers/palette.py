"""Palette analysis (spec §7.1)."""
from __future__ import annotations
from typing import Any

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


def _hierarchy_score(colors: list[int]) -> dict[str, Any]:
    bg_used = [i for i in _DEFAULT_BACKGROUND if i < len(colors)]
    env_used = [i for i in _DEFAULT_ENVIRONMENT if i < len(colors)]
    int_used = [i for i in _DEFAULT_INTERACTIVE if i < len(colors)]
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

    Both fields are returned from one pass to avoid re-scanning ~65k pixels
    per bank twice.
    """
    import pyxel
    used: set[int] = set()
    pairs: set[tuple[int, int]] = set()
    for img in pyxel.images:
        w, h = img.width, img.height
        for y in range(h):
            for x in range(w):
                idx = img.pget(x, y)
                if idx == 0:
                    continue
                used.add(idx)
                # 4-neighbour adjacency (right + down only — undirected).
                if x + 1 < w:
                    nb = img.pget(x + 1, y)
                    if nb != 0 and nb != idx:
                        pairs.add((idx, nb) if idx < nb else (nb, idx))
                if y + 1 < h:
                    nb = img.pget(x, y + 1)
                    if nb != 0 and nb != idx:
                        pairs.add((idx, nb) if idx < nb else (nb, idx))
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
    info: dict[str, Any] = {
        "colors": {i: _hex(c) for i, c in enumerate(colors)},
        "extended_palette": extended,
        "palette_size": len(colors),
        "used_indices": sorted(used),
        "co_located_pairs": sorted(co_located),
        "hierarchy": None if extended else _hierarchy_score(colors),
        "contrast_warnings": _detect_close_pairs(colors, co_located),
        "errors": [],
    }
    return info
