"""judge_sprite — verdict on a read_image observation."""
from __future__ import annotations
from typing import Any

DEFAULT_CONTRACT: dict[str, Any] = {
    "min_distinct_colors": 3,
    "silhouette": [0.15, 0.95],
}


def judge_sprite(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verdict for a `read_image` observation against a sprite manifest entry.

    `observation`: dict with `color_count` (dict[int, int]) and `fill_ratio` (float).
    `contract`: dict; missing keys fall back to DEFAULT_CONTRACT. May include
    a `represents` field (carried into details for traceability).
    """
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    min_colors = c["min_distinct_colors"]
    band = c["silhouette"]
    lo, hi = band[0], band[1]

    color_count = observation.get("color_count") or {}
    n_colors = len(color_count)
    fill = observation.get("fill_ratio", 0.0)

    details: dict[str, Any] = {
        "n_distinct_colors": n_colors,
        "fill_ratio": fill,
        "min_distinct_colors": min_colors,
        "silhouette_band": [lo, hi],
    }
    if "represents" in c:
        details["represents"] = c["represents"]

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
