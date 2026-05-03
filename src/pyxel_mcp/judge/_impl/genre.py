"""judge_genre — verify PLAN.md `## Genre Identity` rules over run result(s).

Each rule is `{name, verify}`; `verify` is a sandboxed predicate evaluated
in a namespace built from run-aggregate signals (exit_status, frame_count,
log, assertions_passed/_failed). Empty rule lists are an authoring failure
(spec route) — genre identity must be explicit.
"""
from __future__ import annotations
from typing import Any

from pyxel_mcp.judge._impl._eval import eval_predicate

DEFAULT_CONTRACT: dict[str, Any] = {"rules": []}


def _build_namespace(observation: dict[str, Any]) -> dict[str, Any]:
    """Aggregate signals a verify predicate can reference."""
    assertions = observation.get("assertions") or []
    return {
        "exit_status": observation.get("exit_status", ""),
        "frame_count": observation.get("frame_count", 0),
        "ok": bool(observation.get("ok", False)),
        "elapsed_seconds": observation.get("elapsed_seconds", 0.0),
        "log": observation.get("log", "") or "",
        "assertions_passed": frozenset(a["name"] for a in assertions if a.get("passed")),
        "assertions_failed": frozenset(a["name"] for a in assertions if not a.get("passed")),
    }


def judge_genre(
    observation: dict[str, Any],
    contract: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate Genre Identity rules against a run result."""
    c = {**DEFAULT_CONTRACT, **(contract or {})}
    rules = c.get("rules") or []

    if not rules:
        return {
            "ok": False,
            "verdict": "fail",
            "evidence": "PLAN.md `## Genre Identity` requires at least one rule — none supplied",
            "fail_route": "spec",
            "details": {"n_rules": 0},
        }

    names = _build_namespace(observation)
    results: list[dict[str, Any]] = []
    for rule in rules:
        name = rule.get("name", "<unnamed>")
        verify = rule.get("verify", "")
        try:
            passed = eval_predicate(verify, names)
        except ValueError as e:
            results.append({
                "name": name, "verify": verify, "passed": False,
                "reason": f"predicate error: {e}", "fail_route": "spec",
            })
            continue
        except NameError as e:
            results.append({
                "name": name, "verify": verify, "passed": False,
                "reason": f"unknown name: {e}", "fail_route": "spec",
            })
            continue
        except (AttributeError, TypeError, KeyError) as e:
            results.append({
                "name": name, "verify": verify, "passed": False,
                "reason": f"evaluation error: {type(e).__name__}: {e}",
                "fail_route": "spec",
            })
            continue

        results.append({
            "name": name, "verify": verify, "passed": passed,
            "reason": "ok" if passed else "rule predicate evaluated False",
            "fail_route": None if passed else "playthrough",
        })

    failed = [r for r in results if not r["passed"]]
    if not failed:
        return {
            "ok": True,
            "verdict": "pass",
            "evidence": f"{len(results)} genre identity rules all passed",
            "fail_route": None,
            "details": {"results": results},
        }

    spec_fails = [r for r in failed if r["fail_route"] == "spec"]
    fail_route = "spec" if spec_fails else "playthrough"
    return {
        "ok": False,
        "verdict": "fail",
        "evidence": f"{len(failed)} of {len(results)} genre rules failed",
        "fail_route": fail_route,
        "details": {"results": results},
    }
