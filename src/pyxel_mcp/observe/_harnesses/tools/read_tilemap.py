"""read_tilemap tool."""
from __future__ import annotations
from typing import Any

from pyxel_mcp.observe._harnesses._common.analyzers.tilemap import analyze_tilemap
from pyxel_mcp.observe._harnesses._common.artifact_path import absolute_path_error
from pyxel_mcp.observe._harnesses._common.error_capture import make_validation_error
from pyxel_mcp.observe._harnesses._common.preloop import PreloopFailed, run_to_preloop


def _empty(error: dict) -> dict:
    return {
        "ok": False,
        "tilemap_index": -1, "size": [0, 0], "imgsrc": 0,
        "tiles": None, "usage": {}, "region": None,
        "trap_warning": False, "rendered": None,
        "warnings": [], "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Inspect a tilemap at the pre-loop checkpoint.

    Result includes `ok: bool` — True iff `len(errors) == 0`. The
    `trap_warning` flag is informational and does not affect `ok`.
    """
    tilemap = payload.get("tilemap")
    if not isinstance(tilemap, int):
        return _empty(make_validation_error("`tilemap` must be int"))
    render_path = payload.get("render_path")
    if render_path is not None:
        path_error = absolute_path_error(render_path, "render_path")
        if path_error:
            return _empty(make_validation_error(path_error))

    try:
        with run_to_preloop(payload, empty_factory=_empty):
            import pyxel
            if tilemap < 0 or tilemap >= len(pyxel.tilemaps):
                return _empty(make_validation_error(
                    f"tilemap index {tilemap} out of range [0, {len(pyxel.tilemaps)})"))

            result = analyze_tilemap(tilemap=tilemap, render_path=render_path)
    except PreloopFailed as f:
        return f.result
    result["ok"] = len(result.get("errors", [])) == 0
    return result
