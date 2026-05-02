"""inspect_tilemap tool (spec §7.4)."""
from __future__ import annotations
from typing import Any

from pyxel_mcp._harnesses._common.error_capture import make_validation_error, make_error, ErrorPhase
from pyxel_mcp._harnesses._common.pyxel_patcher import headless_pyxel, RunNotCalledError
from pyxel_mcp._harnesses._common.script_loader import resolve_script_path, load_script_module
from pyxel_mcp._harnesses._common.analyzers.tilemap import analyze_tilemap


def _empty(error: dict) -> dict:
    return {
        "tilemap_index": -1, "size": [0, 0], "imgsrc": 0,
        "tiles": None, "usage": {}, "bounding_box": None,
        "trap_warning": False, "rendered": None,
        "warnings": [], "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    script = payload.get("script")
    tilemap = payload.get("tilemap")
    if not isinstance(script, str):
        return _empty(make_validation_error("missing or non-str `script`"))
    if not isinstance(tilemap, int):
        return _empty(make_validation_error("`tilemap` must be int"))

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
        if tilemap < 0 or tilemap >= len(pyxel.tilemaps):
            return _empty(make_validation_error(
                f"tilemap index {tilemap} out of range [0, {len(pyxel.tilemaps)})"))

        return analyze_tilemap(tilemap=tilemap, render_path=payload.get("render_path"))
