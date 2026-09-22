"""Subprocess boundary shared by all MCP tools."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Literal

from pyxel_mcp.contracts import RunResult
from pyxel_mcp.observe._harnesses._common.error_capture import ErrorPhase, make_error


def _error(phase: ErrorPhase, message: str) -> dict[str, Any]:
    return {"ok": False, "errors": [make_error(phase, message)]}


def _run_error(
    phase: ErrorPhase,
    message: str,
    *,
    exit_status: Literal["crashed", "timeout", "invalid"] = "crashed",
    elapsed_seconds: float = 0.0,
    log: str = "",
) -> dict[str, Any]:
    return {
        "ok": False,
        "snapshots": [],
        "exit_status": exit_status,
        "frame_count": 0,
        "elapsed_seconds": elapsed_seconds,
        "log": log,
        "seeded": False,
        "until_met": None,
        "errors": [make_error(phase, message)],
    }


def _join_log(current: str, diagnostic: str) -> str:
    if not current:
        return diagnostic
    if not diagnostic:
        return current
    return f"{current.rstrip()}\n{diagnostic.lstrip()}"


_RUN_RESULT_FIELDS = {
    name for name, field in RunResult.model_fields.items() if field.is_required()
}


def _normalize_run_result(result: dict[str, Any]) -> dict[str, Any]:
    """Keep the public RunResult shape intact across unexpected subprocess failures."""
    if _RUN_RESULT_FIELDS <= result.keys():
        return result

    normalized = _run_error(
        ErrorPhase.SCRIPT_IMPORT,
        "subprocess returned an incomplete run result",
    )
    errors = result.get("errors")
    if isinstance(errors, list) and errors:
        normalized["errors"] = errors
    return normalized


def dispatch(
    subcommand: str, payload: dict[str, Any], timeout: int = 60
) -> dict[str, Any]:
    cmd = [sys.executable, "-m", "pyxel_mcp.observe._harnesses.main", subcommand]
    try:
        with tempfile.TemporaryDirectory(prefix="pyxel-mcp-dispatch-") as temp_root:
            # User code and native libraries may write anything to stdout,
            # including JSON from atexit handlers after the tool has finished.
            # Keep the result on a separate channel rather than guessing which
            # line of the script's output belongs to the harness.
            result_path = Path(temp_root) / "result.json"
            cmd.extend(["--result-file", str(result_path)])
            env = os.environ.copy()
            env.update({"TMPDIR": temp_root, "TMP": temp_root, "TEMP": temp_root})
            proc = subprocess.run(
                cmd,
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                env=env,
                check=False,
            )
            result_text = (
                result_path.read_text(encoding="utf-8") if result_path.is_file() else ""
            )
    except subprocess.TimeoutExpired:
        message = f"subprocess timed out after {timeout}s"
        if subcommand == "run":
            return _run_error(
                ErrorPhase.GAME_LOOP,
                message,
                exit_status="timeout",
                elapsed_seconds=float(timeout),
            )
        return _error(ErrorPhase.GAME_LOOP, message)
    except OSError as exc:
        message = f"could not execute subprocess: {exc}"
        if subcommand == "run":
            return _run_error(ErrorPhase.SCRIPT_IMPORT, message)
        return _error(ErrorPhase.SCRIPT_IMPORT, message)

    if proc.returncode != 0:
        message = f"subprocess exited {proc.returncode}: {proc.stderr}"
        if subcommand == "run":
            return _run_error(ErrorPhase.SCRIPT_IMPORT, message, log=proc.stderr)
        return _error(ErrorPhase.SCRIPT_IMPORT, message)

    try:
        result = json.loads(result_text) if result_text.strip() else {}
    except json.JSONDecodeError as exc:
        message = f"subprocess returned invalid JSON: {exc}: {result_text[-500:]}"
        if subcommand == "run":
            return _run_error(ErrorPhase.SCRIPT_IMPORT, message, log=proc.stdout)
        return _error(ErrorPhase.SCRIPT_IMPORT, message)

    if not isinstance(result, dict):
        message = "subprocess JSON payload must be a JSON object"
        if subcommand == "run":
            return _run_error(ErrorPhase.SCRIPT_IMPORT, message, log=proc.stdout)
        return _error(ErrorPhase.SCRIPT_IMPORT, message)

    if not result:
        message = "subprocess returned no JSON payload"
        if subcommand == "run":
            return _run_error(ErrorPhase.SCRIPT_IMPORT, message, log=proc.stdout)
        return _error(ErrorPhase.SCRIPT_IMPORT, message)

    if subcommand == "run":
        result = _normalize_run_result(result)
    if "ok" not in result and "errors" in result:
        result["ok"] = not result["errors"]
    if subcommand == "run":
        result["log"] = _join_log(result.get("log", ""), proc.stderr)
        result["log"] = _join_log(result["log"], proc.stdout)
    return result
