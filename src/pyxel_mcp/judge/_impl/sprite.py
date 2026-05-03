"""judge_sprite — verdict on a `read_image` observation."""
from __future__ import annotations
from typing import Any

# Fallback when the observation has no `region` (synthetic input). For real
# observations the area is read off the region and translated into a
# threshold by `_scale_min_distinct_colors_to_area` below.
DEFAULT_CONTRACT: dict[str, Any] = {
    "min_distinct_colors": 3,
    "silhouette": [0.15, 0.95],
}


def _scale_min_distinct_colors_to_area(area: int) -> int:
    """Return the natural minimum-colour count for a sprite of this area.

    Pre-fix this was a flat 3 — fine for 16×16 player sprites, hostile
    to 4×4 balls / bullets / sparks where 16 pixels can't be both
    silhouetted AND tri-toned without single-pixel colour blobs. The
    e2e validation hit exactly this case and had to override.
    """
    if area <= 16:   # 4×4 or smaller — outline + body is plenty
        return 2
    if area <= 64:   # 8×8 — outline + body + shading
        return 3
    return 4         # 16×16 and up — there's room for a real palette


def judge_sprite(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verdict for a `read_image` observation against a sprite manifest entry.

    `observation`: dict with `color_count` (dict[int, int]), `fill_ratio`
    (float), and `region` ({x, y, w, h}). Region area is used to pick
    a sensible `min_distinct_colors` floor unless the contract overrides
    it explicitly. `contract`: dict; an explicit `min_distinct_colors`
    always wins over the area-derived default. May include a
    `represents` field (carried into details for traceability).
    """
    user_contract = contract or {}
    region = observation.get("region") or {}
    area = int(region.get("w", 0)) * int(region.get("h", 0))

    if "min_distinct_colors" in user_contract:
        min_colors = user_contract["min_distinct_colors"]
    elif area > 0:
        min_colors = _scale_min_distinct_colors_to_area(area)
    else:
        min_colors = DEFAULT_CONTRACT["min_distinct_colors"]

    band = user_contract.get("silhouette", DEFAULT_CONTRACT["silhouette"])
    lo, hi = band[0], band[1]

    color_count = observation.get("color_count") or {}
    n_colors = len(color_count)
    fill = observation.get("fill_ratio", 0.0)

    details: dict[str, Any] = {
        "n_distinct_colors": n_colors,
        "fill_ratio": fill,
        "min_distinct_colors": min_colors,
        "silhouette_band": [lo, hi],
        "sprite_area": area,
    }
    if "represents" in user_contract:
        details["represents"] = user_contract["represents"]

    if n_colors < min_colors:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"only {n_colors} distinct colors, need >= {min_colors}",
            "fail_route": "sprite-quality",
            "details": details,
        }

    if not (lo <= fill <= hi):
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"fill_ratio {fill:.3f} outside silhouette band [{lo}, {hi}]",
            "fail_route": "sprite-quality",
            "details": details,
        }

    return {
        "ok": True,
        "verdict": "pass",
        "evidence": f"{n_colors} colors, fill {fill:.3f} within [{lo}, {hi}]",
        "fail_route": None,
        "details": details,
    }
