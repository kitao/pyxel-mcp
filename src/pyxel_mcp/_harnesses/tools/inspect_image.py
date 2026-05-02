"""inspect_image tool (spec §7.2)."""
from __future__ import annotations
from typing import Any

from pyxel_mcp._harnesses._common.error_capture import make_validation_error, make_error, ErrorPhase
from pyxel_mcp._harnesses._common.pyxel_patcher import headless_pyxel, RunNotCalledError
from pyxel_mcp._harnesses._common.script_loader import resolve_script_path, load_script_module
from pyxel_mcp._harnesses._common.analyzers.image import analyze_image


def _empty(error: dict) -> dict:
    return {
        "image_index": -1, "bank_size": [0, 0],
        "region": {"x": 0, "y": 0, "w": 0, "h": 0},
        "pixels": None, "color_count": {}, "fill_ratio": 0.0,
        "symmetry": None, "edge_density": None,
        "warnings": [], "rendered": None, "verdict": None,
        "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    script = payload.get("script")
    image = payload.get("image")
    if not isinstance(script, str):
        return _empty(make_validation_error("missing or non-str `script`"))
    if not isinstance(image, int):
        return _empty(make_validation_error("`image` must be int"))

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

        return analyze_image(
            image=image,
            x=payload.get("x", 0), y=payload.get("y", 0),
            w=payload.get("w"), h=payload.get("h"),
            render_path=payload.get("render_path"),
        )
