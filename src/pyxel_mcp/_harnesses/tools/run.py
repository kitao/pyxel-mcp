"""run(script, frames, ...) — dynamic execution driver (spec §6)."""
from __future__ import annotations
import contextlib
import time
import traceback as _tb
from io import StringIO
from typing import Any

from pyxel_mcp._harnesses._common.error_capture import (
    make_error, make_validation_error, ErrorPhase,
)
from pyxel_mcp._harnesses._common.pyxel_patcher import headless_pyxel, RunNotCalledError
from pyxel_mcp._harnesses._common.script_loader import resolve_script_path, load_script_module


class _ValidationFailed(Exception):
    """Raised internally when payload validation fails; carries the error dict."""

    def __init__(self, err: dict):
        self.err = err


def _empty_result(*, exit_status: str = "ok", errors: list | None = None) -> dict:
    return {
        "snapshots": [],
        "assertions": [],
        "exit_status": exit_status,
        "frame_count": 0,
        "elapsed_seconds": 0.0,
        "log": "",
        "seeded": False,
        "errors": errors or [],
    }


def _validate(payload: dict[str, Any]) -> tuple[Any, ...]:
    """Validate payload and return (script_path, frames, random_seed).

    Raises _ValidationFailed with a ToolError dict on any invalid input.
    """
    script = payload.get("script")
    if not isinstance(script, str):
        raise _ValidationFailed(make_validation_error("missing or non-str `script`"))

    frames = payload.get("frames")
    if not isinstance(frames, int) or frames < 1:
        raise _ValidationFailed(make_validation_error("`frames` must be int >= 1"))

    try:
        path = resolve_script_path(script)
    except FileNotFoundError as e:
        raise _ValidationFailed(make_validation_error(str(e), path=script))

    random_seed = payload.get("random_seed")
    if random_seed is not None and (not isinstance(random_seed, int) or random_seed < 0):
        raise _ValidationFailed(make_validation_error("`random_seed` must be non-negative int"))

    timeout = payload.get("timeout", 10)
    if not isinstance(timeout, int) or timeout < 1:
        raise _ValidationFailed(make_validation_error("`timeout` must be int >= 1"))
    # timeout is informational at this layer; server enforces wall-clock kill.

    return path, frames, random_seed


def _is_asset_load_error(tb_text: str) -> bool:
    """Heuristic: classify an exception as asset_load if the traceback text
    mentions patterns produced by Pyxel's file-open failures.

    Pyxel 2.9.4 raises a generic Exception with message "Failed to open file
    '<path>'". Python FileNotFoundError and "could not open" are kept as
    additional guards for forward compatibility.

    Caveat: this is a string-match heuristic — a user script that raises a
    custom exception whose message happens to contain these phrases will be
    misclassified as asset_load. Acceptable for v0.9.3 since Pyxel doesn't
    expose typed exceptions; revisit if a typed asset-error API ships.
    """
    lower = tb_text.lower()
    return (
        "filenotfounderror" in tb_text
        or "could not open" in lower
        or "failed to open file" in lower
    )


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Execute a Pyxel script for a fixed number of frames and return a RunResult.

    Validates the payload, loads the script inside a headless Pyxel context,
    then drives the update/draw loop for the requested number of frames.
    Errors are caught per-phase and reported in the `errors` list rather than
    raised, so callers always receive a well-formed result dict.
    """
    try:
        path, frames, random_seed = _validate(payload)
    except _ValidationFailed as vf:
        return _empty_result(exit_status="invalid", errors=[vf.err])

    started = time.monotonic()
    errors: list[dict] = []
    seeded = False
    frame_count = 0
    exit_status = "ok"

    # Capture stdout+stderr from the user script into log_buf.
    # The real stdout is reserved for the JSON result written by main.py,
    # so the redirect must be closed before run() returns.
    log_buf = StringIO()
    with headless_pyxel() as state:
        with contextlib.redirect_stdout(log_buf), contextlib.redirect_stderr(log_buf):
            # Phase 1: import script (pyxel.run is intercepted by headless_pyxel)
            try:
                load_script_module(path)
            except FileNotFoundError as e:
                # Asset path is in the exception message; we don't know it here.
                errors.append(make_error(
                    ErrorPhase.ASSET_LOAD, str(e), capture_traceback=True,
                ))
                exit_status = "crashed"
            except Exception as e:
                tb_text = _tb.format_exc()
                if _is_asset_load_error(tb_text):
                    errors.append(make_error(
                        ErrorPhase.ASSET_LOAD, str(e), capture_traceback=True,
                    ))
                else:
                    errors.append(make_error(
                        ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=True,
                    ))
                exit_status = "crashed"

            if not errors:
                try:
                    state.require_run_called()
                except RunNotCalledError as e:
                    errors.append(make_error(
                        ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=False,
                    ))
                    exit_status = "crashed"

            if not errors:
                import pyxel

                # Phase 2: pre-loop checkpoint — seed RNG if requested
                if random_seed is not None:
                    pyxel.rseed(random_seed)
                    seeded = True

                # Phase 3: drive the update/draw loop
                for f in range(frames):
                    try:
                        pyxel.frame_count = f
                        state.update_callback()
                        state.draw_callback()
                        frame_count = f + 1
                    except Exception as e:
                        errors.append(make_error(
                            ErrorPhase.GAME_LOOP, str(e), frame=f, capture_traceback=True,
                        ))
                        exit_status = "crashed"
                        frame_count = f
                        break
    # redirect_stdout/stderr context is now closed — real stdout is restored
    log_text = log_buf.getvalue()

    elapsed = time.monotonic() - started
    return {
        "snapshots": [],
        "assertions": [],
        "exit_status": exit_status,
        "frame_count": frame_count,
        "elapsed_seconds": elapsed,
        "log": log_text,
        "seeded": seeded,
        "errors": errors,
    }
