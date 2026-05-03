"""judge_animation — verdict on an inspect_animation observation."""
from __future__ import annotations
from typing import Any

DEFAULT_CONTRACT: dict[str, Any] = {
    "diff_band": [0.05, 0.50],
    "min_palette_consistency": 1.0,
}


def judge_animation(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verdict for an `inspect_animation` observation.

    Pass requires every adjacent-region diff to fall within `diff_band`
    and `palette_consistency` to meet `min_palette_consistency`.
    """
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    band = c["diff_band"]
    lo, hi = band[0], band[1]
    min_pc = c["min_palette_consistency"]

    region_diffs = observation.get("region_diffs") or []
    pc = observation.get("palette_consistency", 0.0)

    diff_ratios = [d.get("diff_ratio", 0.0) for d in region_diffs]
    details: dict[str, Any] = {
        "diff_ratios": diff_ratios,
        "palette_consistency": pc,
        "diff_band": [lo, hi],
        "min_palette_consistency": min_pc,
    }

    if not region_diffs:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": "no region_diffs available (region_count must be >= 2)",
            "fail_route": "sprite-quality",
            "details": details,
        }

    out_of_band = [r for r in diff_ratios if not (lo <= r <= hi)]
    if out_of_band:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"{len(out_of_band)} of {len(diff_ratios)} diff_ratios outside [{lo}, {hi}]: {out_of_band}",
            "fail_route": "sprite-quality",
            "details": details,
        }

    if pc < min_pc:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"palette_consistency {pc:.3f} below required {min_pc}",
            "fail_route": "sprite-quality",
            "details": details,
        }

    return {
        "ok": True,
        "verdict": "pass",
        "evidence": f"{len(diff_ratios)} diffs in [{lo}, {hi}], consistency {pc:.3f} >= {min_pc}",
        "fail_route": None,
        "details": details,
    }
