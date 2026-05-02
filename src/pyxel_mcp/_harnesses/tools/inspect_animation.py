"""inspect_animation tool (spec §7.3)."""
from __future__ import annotations
from typing import Any

from pyxel_mcp._harnesses._common.analyzers.animation import analyze_animation
from pyxel_mcp._harnesses._common.error_capture import make_validation_error
from pyxel_mcp._harnesses._common.preloop import PreloopFailed, run_to_preloop


def _empty(error: dict) -> dict:
    return {
        "ok": False,
        "image_index": -1,
        "regions": [],
        "palette_consistency": 0.0,
        "silhouette_stability": 0.0,
        "region_diffs": [],
        "warnings": [],
        "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Inspect adjacent regions in an image bank for animation consistency.

    Result includes `ok: bool` — True iff `len(errors) == 0`.
    """
    image = payload.get("image", 0)
    x = payload.get("x", 0)
    y = payload.get("y", 0)
    w = payload.get("w")
    h = payload.get("h")
    region_count = payload.get("region_count")
    direction = payload.get("direction", "horizontal")

    if not isinstance(image, int):
        return _empty(make_validation_error("`image` must be int"))
    if not isinstance(region_count, int) or region_count < 2:
        return _empty(make_validation_error("`region_count` must be int >= 2"))
    if not isinstance(w, int) or not isinstance(h, int):
        return _empty(make_validation_error("`w` and `h` must be int"))

    try:
        with run_to_preloop(payload, empty_factory=_empty):
            import pyxel
            if image < 0 or image >= len(pyxel.images):
                return _empty(make_validation_error(
                    f"image index {image} out of range [0, {len(pyxel.images)})"))

            try:
                result = analyze_animation(
                    image=image, x=x, y=y, w=w, h=h,
                    region_count=region_count, direction=direction,
                )
            except ValueError as e:
                return _empty(make_validation_error(str(e)))
    except PreloopFailed as f:
        return f.result
    result["ok"] = len(result.get("errors", [])) == 0
    return result
