"""inspect_palette tool (spec §7.1).

Runs the script to the pre-loop checkpoint, then analyzes the palette.
"""
from __future__ import annotations
from typing import Any

from pyxel_mcp.observe._harnesses._common.analyzers.palette import analyze_palette
from pyxel_mcp.observe._harnesses._common.preloop import PreloopFailed, run_to_preloop


def _empty(error: dict) -> dict[str, Any]:
    """Error-shape response — verdict is None (no analysis performed)."""
    return {
        "ok": False,
        "colors": {}, "extended_palette": False, "palette_size": 0,
        "hierarchy": None, "contrast_warnings": [], "verdict": None,
        "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Inspect the script's palette state at the pre-loop checkpoint.

    Result includes `ok: bool` — True iff `len(errors) == 0`. The `verdict`
    field is informational (pass/warn/fail/null) and does not affect `ok`.
    """
    try:
        with run_to_preloop(payload, empty_factory=_empty):
            result = analyze_palette()
    except PreloopFailed as f:
        return f.result
    result["ok"] = len(result.get("errors", [])) == 0
    return result
