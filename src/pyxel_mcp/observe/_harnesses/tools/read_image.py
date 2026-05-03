"""read_image tool (spec §7.2)."""
from __future__ import annotations
from typing import Any

from pyxel_mcp.observe._harnesses._common.analyzers.image import analyze_image
from pyxel_mcp.observe._harnesses._common.error_capture import make_validation_error
from pyxel_mcp.observe._harnesses._common.preloop import PreloopFailed, run_to_preloop


def _empty(error: dict) -> dict:
    return {
        "ok": False,
        "image_index": -1, "bank_size": [0, 0],
        "region": {"x": 0, "y": 0, "w": 0, "h": 0},
        "pixels": None, "color_count": {}, "fill_ratio": 0.0,
        "symmetry": None, "edge_density": None,
        "warnings": [], "rendered": None,
        "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Read pixels in an image-bank region at the pre-loop checkpoint.

    Returns raw observation (`color_count`, `fill_ratio`, ...). The agent
    judges the verdict directly: compare aggregates to ASSETS.md sprite
    manifest entry, then `Read` the rendered PNG (pass `render_path`)
    and verbalize against the `represents:` description. `ok` is True
    iff `len(errors) == 0`.
    """
    image = payload.get("image")
    if not isinstance(image, int):
        return _empty(make_validation_error("`image` must be int"))

    try:
        with run_to_preloop(payload, empty_factory=_empty):
            import pyxel
            if image < 0 or image >= len(pyxel.images):
                return _empty(make_validation_error(
                    f"image index {image} out of range [0, {len(pyxel.images)})"))

            result = analyze_image(
                image=image,
                x=payload.get("x", 0), y=payload.get("y", 0),
                w=payload.get("w"), h=payload.get("h"),
                render_path=payload.get("render_path"),
            )
    except PreloopFailed as f:
        return f.result
    result["ok"] = len(result.get("errors", [])) == 0
    return result
