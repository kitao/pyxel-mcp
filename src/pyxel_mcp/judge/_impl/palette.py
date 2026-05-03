"""judge_palette — verdict on a palette observation.

Returns two independent sub-verdicts (hierarchy, contrast) plus an
overall worst-of-the-two `verdict`. quality-gate.md's checks #8 (palette
hierarchy) and #9 (contrast) read from the same observation, but they
score against different criteria — surfacing them separately means a
contrast-only failure no longer causes #8 to render as FAIL too. The
top-level `verdict` / `ok` / `fail_route` fields stay backwards
compatible (worst-of), so existing callers that don't yet read
`sub_verdicts` keep working.
"""
from __future__ import annotations
from typing import Any

# Contrast warnings: pass at ≤ max, warn for the next _WARN_BAND, fail above.
_WARN_BAND = 4

# Hierarchy: pass at ≥ min, warn 1 below, fail 2+ below.
_HIERARCHY_WARN_DROP = 1

# `max_contrast_warnings` default tuned to the skill's own 3-color-per-material
# rule (shadow / base / highlight per material): a 3-material game produces
# 9-12 unavoidable low-contrast pairs, so a default of 1 forced every retro
# game with multiple materials to override. 5 admits the natural pattern
# while still flagging palettes that overshoot it.
DEFAULT_CONTRACT: dict[str, Any] = {
    "min_hierarchy_score": 2,
    "max_contrast_warnings": 5,
}

_RANK = {"pass": 0, "warn": 1, "fail": 2}


def _hierarchy_sub_verdict(score: int, min_score: int) -> tuple[str, str]:
    if score >= min_score:
        return "pass", f"score {score} >= {min_score}"
    if score >= min_score - _HIERARCHY_WARN_DROP:
        return "warn", f"score {score} just below required {min_score}"
    return "fail", f"score {score} below required {min_score}"


def _contrast_sub_verdict(n_warn: int, max_warn: int) -> tuple[str, str]:
    if n_warn <= max_warn:
        return "pass", f"{n_warn} contrast warnings <= {max_warn}"
    if n_warn <= max_warn + _WARN_BAND:
        return "warn", (
            f"{n_warn} contrast warnings (allowance {max_warn}) — actionable"
        )
    return "fail", (
        f"{n_warn} contrast warnings exceeds limit {max_warn + _WARN_BAND}"
    )


def _overall(h: str, c: str) -> str:
    worst = max(_RANK[h], _RANK[c])
    return {0: "pass", 1: "warn", 2: "fail"}[worst]


def judge_palette(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verdict for a `read_palette` observation.

    `observation`: dict with `hierarchy` ({"score": int} or None) and
    `contrast_warnings` (list).
    `contract`: dict; missing keys fall back to DEFAULT_CONTRACT.

    Returns dict with:
    - `ok` (bool — True when verdict != fail)
    - `verdict` ('pass'|'warn'|'fail') — worst of the two sub-verdicts
    - `evidence` (one-line summary of both sub-verdicts)
    - `fail_route` ('asset-planning'|'sprite-quality'|None)
    - `details`
    - `sub_verdicts` ({'hierarchy': ..., 'contrast': ...})
    """
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    min_score = c["min_hierarchy_score"]
    max_warn = c["max_contrast_warnings"]

    hierarchy = observation.get("hierarchy")
    warnings = observation.get("contrast_warnings") or []
    n_warn = len(warnings)

    if hierarchy is None:
        # Extended palette — hierarchy check is n/a, contrast still applies.
        h_verdict, h_reason = "pass", "extended palette — hierarchy check skipped"
        score = None
    else:
        score = hierarchy.get("score", 0)
        h_verdict, h_reason = _hierarchy_sub_verdict(score, min_score)

    c_verdict, c_reason = _contrast_sub_verdict(n_warn, max_warn)
    overall = _overall(h_verdict, c_verdict)

    if h_verdict == "fail":
        fail_route: str | None = "asset-planning"
    elif c_verdict == "fail":
        fail_route = "sprite-quality"
    else:
        fail_route = None

    details: dict[str, Any] = {
        "score": score,
        "n_warnings": n_warn,
        "min_score": min_score,
        "max_warnings": max_warn,
        "extended_palette": hierarchy is None,
    }

    return {
        "ok": overall != "fail",
        "verdict": overall,
        "evidence": f"hierarchy {h_verdict} ({h_reason}); contrast {c_verdict} ({c_reason})",
        "fail_route": fail_route,
        "details": details,
        "sub_verdicts": {
            "hierarchy": h_verdict,
            "contrast": c_verdict,
        },
    }
