"""judge_palette — verdict on a palette observation."""
from __future__ import annotations
from typing import Any

# pass/warn boundary is `max_contrast_warnings`; warn/fail boundary is
# max_contrast_warnings + _WARN_BAND. Mirrors the historic 1/5 thresholds.
_WARN_BAND = 4

DEFAULT_CONTRACT: dict[str, Any] = {
    "min_hierarchy_score": 2,
    "max_contrast_warnings": 1,
}


def judge_palette(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verdict for an `inspect_palette` observation.

    `observation`: dict with `hierarchy` ({"score": int} or None) and
    `contrast_warnings` (list).
    `contract`: dict; missing keys fall back to DEFAULT_CONTRACT.

    Returns dict with: ok, verdict ('pass'|'warn'|'fail'), evidence,
    fail_route ('asset-planning'|'sprite-quality'|None), details.
    """
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    min_score = c["min_hierarchy_score"]
    max_warn = c["max_contrast_warnings"]

    hierarchy = observation.get("hierarchy")
    warnings = observation.get("contrast_warnings") or []
    n_warn = len(warnings)

    if hierarchy is None:
        return {
            "ok": True,
            "verdict": "pass",
            "evidence": "extended palette — hierarchy check skipped",
            "fail_route": None,
            "details": {"extended_palette": True, "n_warnings": n_warn},
        }

    score = hierarchy.get("score", 0)
    details = {
        "score": score,
        "n_warnings": n_warn,
        "min_score": min_score,
        "max_warnings": max_warn,
    }

    if score < min_score:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"hierarchy score {score} below required {min_score}",
            "fail_route": "asset-planning",
            "details": details,
        }

    if n_warn > max_warn + _WARN_BAND:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"{n_warn} contrast warnings exceeds limit {max_warn + _WARN_BAND}",
            "fail_route": "sprite-quality",
            "details": details,
        }

    if n_warn > max_warn:
        return {
            "ok": True,
            "verdict": "warn",
            "evidence": f"{n_warn} contrast warnings (allowance {max_warn}) — actionable",
            "fail_route": None,
            "details": details,
        }

    return {
        "ok": True,
        "verdict": "pass",
        "evidence": f"score {score} >= {min_score}, {n_warn} warnings <= {max_warn}",
        "fail_route": None,
        "details": details,
    }
