"""read_palette tool (spec §7.1).

Runs the script to the pre-loop checkpoint, then analyzes the palette.
"""
from __future__ import annotations
from typing import Any

from pyxel_mcp.observe._harnesses._common.analyzers.palette import analyze_palette
from pyxel_mcp.observe._harnesses._common.preloop import PreloopFailed, run_to_preloop


def _empty(error: dict) -> dict[str, Any]:
    """Error-shape response (no analysis performed)."""
    return {
        "ok": False,
        "colors": {}, "extended_palette": False, "palette_size": 0,
        "used_indices": [], "co_located_pairs": [],
        "hierarchy": None, "contrast_warnings": [],
        "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Read the script's palette state at the pre-loop checkpoint.

    Returns raw observation (`used_indices`, `hierarchy`,
    `contrast_warnings`, ...). `used_indices` reflects the pre-loop image
    banks only; colors drawn at runtime (HUD, overlays) appear in
    `screen_grid` snapshots, so merge the grid's values yourself when
    runtime coverage matters. `ok` is True iff `len(errors) == 0`.
    """
    try:
        with run_to_preloop(payload, empty_factory=_empty):
            result = analyze_palette()
    except PreloopFailed as f:
        return f.result
    result["ok"] = len(result.get("errors", [])) == 0
    return result
