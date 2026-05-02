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


def _detect_close_pairs(colors: list[int]) -> list[dict[str, Any]]:
    """Pairwise WCAG contrast; warn for ratio < 3.0 between any two distinct indices."""
    out: list[dict[str, Any]] = []
    for i in range(len(colors)):
        for j in range(i + 1, len(colors)):
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
    info: dict[str, Any] = {
        "colors": {i: _hex(c) for i, c in enumerate(colors)},
        "extended_palette": extended,
        "palette_size": len(colors),
        "hierarchy": None if extended else _hierarchy_score(colors),
        "contrast_warnings": _detect_close_pairs(colors),
        "errors": [],
    }
    return info
