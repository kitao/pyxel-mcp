"""judge_milestone — Pattern D evaluator for run snapshots.

Index snapshots by `(kind, frame)`, then evaluate per-frame predicates
(sourced from PLAN.md milestones) in a sandboxed namespace built from each
snapshot's payload.
"""
from __future__ import annotations
from typing import Any

from pyxel_mcp.judge._impl._eval import eval_predicate

DEFAULT_CONTRACT: dict[str, Any] = {"asserts": []}


def _snapshot_namespace(snap: dict[str, Any]) -> dict[str, Any]:
    """Flatten a snapshot dict into the name mapping a predicate sees.

    `state` snapshots expose the `values` dict directly. Other kinds expose
    their top-level fields (excluding meta: `frame`, `kind`, `warnings`).
    """
    if snap.get("kind") == "state":
        return dict(snap.get("values") or {})
    return {k: v for k, v in snap.items() if k not in ("frame", "kind", "warnings")}


def _index_snapshots(snapshots: list[dict[str, Any]]) -> dict[tuple[str, int], dict[str, Any]]:
    table: dict[tuple[str, int], dict[str, Any]] = {}
    for snap in snapshots:
        kind = snap.get("kind")
        frame = snap.get("frame")
        if kind is None or frame is None:
            continue
        table[(kind, frame)] = snap
    return table


def judge_milestone(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate PLAN.md milestone asserts against a run() result."""
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    asserts = c.get("asserts") or []

    if observation.get("exit_status") == "crashed":
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": "run crashed before milestones could be evaluated",
            "fail_route": "playthrough",
            "details": {"exit_status": "crashed", "errors": observation.get("errors", [])},
        }

    snapshots = observation.get("snapshots") or []
    table = _index_snapshots(snapshots)

    if not asserts:
        return {
            "ok": True,
            "verdict": "pass",
            "evidence": "no asserts in contract — trivially pass",
            "fail_route": None,
            "details": {"n_asserts": 0},
        }

    results: list[dict[str, Any]] = []
    for a in asserts:
        frame = a.get("frame")
        kind = a.get("kind", "state")
        predicate = a.get("predicate", "")
        snap = table.get((kind, frame))

        if snap is None:
            results.append({
                "predicate": predicate, "frame": frame, "kind": kind,
                "passed": False, "reason": f"no {kind} snapshot at frame {frame}",
                "fail_route": "playthrough",
            })
            continue

        names = _snapshot_namespace(snap)
        try:
            passed = eval_predicate(predicate, names)
        except ValueError as e:
            results.append({
                "predicate": predicate, "frame": frame, "kind": kind,
                "passed": False, "reason": f"predicate error: {e}", "fail_route": "spec",
            })
            continue
        except NameError as e:
            results.append({
                "predicate": predicate, "frame": frame, "kind": kind,
                "passed": False, "reason": f"unknown name: {e}", "fail_route": "spec",
            })
            continue
        except (AttributeError, TypeError, KeyError) as e:
            results.append({
                "predicate": predicate, "frame": frame, "kind": kind,
                "passed": False, "reason": f"evaluation error: {type(e).__name__}: {e}",
                "fail_route": "spec",
            })
            continue

        results.append({
            "predicate": predicate, "frame": frame, "kind": kind,
            "passed": passed,
            "reason": "ok" if passed else "predicate evaluated False",
            "fail_route": None if passed else "playthrough",
        })

    failed = [r for r in results if not r["passed"]]
    if not failed:
        return {
            "ok": True,
            "verdict": "pass",
            "evidence": f"{len(results)} milestone asserts all passed",
            "fail_route": None,
            "details": {"results": results},
        }

    spec_fails = [r for r in failed if r["fail_route"] == "spec"]
    fail_route = "spec" if spec_fails else "playthrough"
    return {
        "ok": False,
        "verdict": "fail",
        "evidence": f"{len(failed)} of {len(results)} milestone asserts failed",
        "fail_route": fail_route,
        "details": {"results": results},
    }
