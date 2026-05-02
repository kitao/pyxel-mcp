"""inspect_animation tool (spec §7.3)."""
from __future__ import annotations
from typing import Any

from pyxel_mcp._harnesses._common.error_capture import make_validation_error, make_error, ErrorPhase
from pyxel_mcp._harnesses._common.pyxel_patcher import headless_pyxel, RunNotCalledError
from pyxel_mcp._harnesses._common.script_loader import resolve_script_path, load_script_module
from pyxel_mcp._harnesses._common.analyzers.animation import analyze_animation


def _empty(error: dict) -> dict:
    return {
        "image_index": -1,
        "regions": [],
        "palette_consistency": 0.0,
        "silhouette_stability": 0.0,
        "region_diffs": [],
        "warnings": [],
        "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    script = payload.get("script")
    image = payload.get("image", 0)
    x = payload.get("x", 0)
    y = payload.get("y", 0)
    w = payload.get("w")
    h = payload.get("h")
    region_count = payload.get("region_count")
    direction = payload.get("direction", "horizontal")

    if not isinstance(script, str):
        return _empty(make_validation_error("missing or non-str `script`"))
    if not isinstance(image, int):
        return _empty(make_validation_error("`image` must be int"))
    if not isinstance(region_count, int) or region_count < 2:
        return _empty(make_validation_error("`region_count` must be int >= 2"))
    if not isinstance(w, int) or not isinstance(h, int):
        return _empty(make_validation_error("`w` and `h` must be int"))

    try:
        path = resolve_script_path(script)
    except FileNotFoundError as e:
        return _empty(make_validation_error(str(e), path=script))

    with headless_pyxel() as state:
        try:
            load_script_module(path)
            state.require_run_called()
        except RunNotCalledError as e:
            return _empty(make_error(ErrorPhase.SCRIPT_IMPORT, str(e)))
        except Exception as e:
            return _empty(make_error(ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=True))

        import pyxel
        if image < 0 or image >= len(pyxel.images):
            return _empty(make_validation_error(
                f"image index {image} out of range [0, {len(pyxel.images)})"))

        try:
            return analyze_animation(
                image=image, x=x, y=y, w=w, h=h,
                region_count=region_count, direction=direction,
            )
        except ValueError as e:
            return _empty(make_validation_error(str(e)))
