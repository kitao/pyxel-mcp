"""inspect_palette tool (spec §7.1).

Runs the script to the pre-loop checkpoint, then analyzes the palette.
"""
from __future__ import annotations
from typing import Any

from pyxel_mcp._harnesses._common.error_capture import make_validation_error, make_error, ErrorPhase
from pyxel_mcp._harnesses._common.pyxel_patcher import headless_pyxel, RunNotCalledError
from pyxel_mcp._harnesses._common.script_loader import resolve_script_path, load_script_module
from pyxel_mcp._harnesses._common.analyzers.palette import analyze_palette


def run(payload: dict[str, Any]) -> dict[str, Any]:
    script = payload.get("script")
    if not isinstance(script, str):
        return {
            "colors": {}, "extended_palette": False, "palette_size": 0,
            "hierarchy": None, "contrast_warnings": [],
            "errors": [make_validation_error("missing or non-str `script`")],
        }
    try:
        path = resolve_script_path(script)
    except FileNotFoundError as e:
        return {
            "colors": {}, "extended_palette": False, "palette_size": 0,
            "hierarchy": None, "contrast_warnings": [],
            "errors": [make_validation_error(str(e), path=script)],
        }

    with headless_pyxel() as state:
        try:
            load_script_module(path)
            state.require_run_called()
        except RunNotCalledError as e:
            return {
                "colors": {}, "extended_palette": False, "palette_size": 0,
                "hierarchy": None, "contrast_warnings": [],
                "errors": [make_error(ErrorPhase.SCRIPT_IMPORT, str(e))],
            }
        except Exception as e:
            return {
                "colors": {}, "extended_palette": False, "palette_size": 0,
                "hierarchy": None, "contrast_warnings": [],
                "errors": [make_error(ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=True)],
            }

        return analyze_palette()
