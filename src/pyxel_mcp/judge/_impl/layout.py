"""judge_layout — verdict on a layout snapshot from a run() result."""
from __future__ import annotations
from typing import Any

DEFAULT_CONTRACT: dict[str, Any] = {
    "min_h_balance": 0.70,
    "min_quadrant_density": 0.0001,
}


def _first_layout_snapshot(observation: dict[str, Any]) -> dict[str, Any] | None:
    for snap in observation.get("snapshots") or []:
        if snap.get("kind") == "layout":
            return snap
    return None


def judge_layout(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verdict for the first layout snapshot in a run() result."""
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    min_h = c["min_h_balance"]
    min_q = c["min_quadrant_density"]

    snap = _first_layout_snapshot(observation)
    if snap is None:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": "no layout snapshot in run result (schedule one with `kind: 'layout'`)",
            "fail_route": "scaffolding",
            "details": {"min_h_balance": min_h, "min_quadrant_density": min_q},
        }

    h = snap.get("h_balance", 0.0)
    quadrants = snap.get("quadrant_density") or [0.0, 0.0, 0.0, 0.0]
    empty_quadrants = [i for i, q in enumerate(quadrants) if q < min_q]

    details = {
        "evaluated_frame": snap.get("frame"),
        "h_balance": h,
        "quadrant_density": quadrants,
        "empty_quadrants": empty_quadrants,
        "min_h_balance": min_h,
        "min_quadrant_density": min_q,
    }

    if h < min_h:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"h_balance {h:.3f} below required {min_h}",
            "fail_route": "scaffolding",
            "details": details,
        }

    if empty_quadrants:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"quadrants {empty_quadrants} below density floor {min_q}",
            "fail_route": "scaffolding",
            "details": details,
        }

    return {
        "ok": True,
        "verdict": "pass",
        "evidence": f"h_balance {h:.3f} >= {min_h}, all quadrants populated",
        "fail_route": None,
        "details": details,
    }
