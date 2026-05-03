"""judge_audio — verdict on a render_audio observation."""
from __future__ import annotations
from typing import Any

DEFAULT_CONTRACT: dict[str, Any] = {
    "min_peak": 0.02,
    "min_notes": 1,
}


def _is_empty_slot(observation: dict[str, Any]) -> bool:
    """Detect the 'slot empty / not populated' warning that render_audio
    emits when a Sound or Music slot was never assigned."""
    for w in observation.get("warnings") or []:
        if "empty" in w and ("not populated" in w or "slot" in w):
            return True
    return False


def judge_audio(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Verdict for a `render_audio` observation against an audio manifest entry."""
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    min_peak = c["min_peak"]
    min_notes = c["min_notes"]

    peak = observation.get("peak_amplitude", 0.0)
    notes = observation.get("notes") or []
    details = {
        "peak_amplitude": peak,
        "n_notes": len(notes),
        "min_peak": min_peak,
        "min_notes": min_notes,
    }

    if _is_empty_slot(observation):
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": "audio slot is empty (asset not generated)",
            "fail_route": "sprite-quality",
            "details": details,
        }

    if peak < min_peak:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"peak amplitude {peak:.4f} below required {min_peak}",
            "fail_route": "scaffolding",
            "details": details,
        }

    if len(notes) < min_notes:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": f"only {len(notes)} notes, need >= {min_notes}",
            "fail_route": "scaffolding",
            "details": details,
        }

    return {
        "ok": True,
        "verdict": "pass",
        "evidence": f"peak {peak:.4f} >= {min_peak}, {len(notes)} notes >= {min_notes}",
        "fail_route": None,
        "details": details,
    }
