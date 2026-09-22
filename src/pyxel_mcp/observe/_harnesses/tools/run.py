"""run(script, frames, ...) — dynamic execution driver."""

from __future__ import annotations

import contextlib
import re
import sys
import time
import traceback as _tb
from io import StringIO
from pathlib import Path
from typing import Any

from PIL import Image
from pydantic import ValidationError as ModelValidationError

from pyxel_mcp.contracts import RunRequest
from pyxel_mcp.observe._harnesses._common.artifact_path import absolute_path_error
from pyxel_mcp.observe._harnesses._common.error_capture import (
    ErrorPhase,
    make_error,
    make_validation_error,
)
from pyxel_mcp.observe._harnesses._common.input_scheduler import (
    InputScheduler,
    ValidationError,
)
from pyxel_mcp.observe._harnesses._common.pyxel_patcher import (
    ObservationFinished,
    PreLoopState,
    QuitRequested,
    RunNotCalledError,
    headless_pyxel,
)
from pyxel_mcp.observe._harnesses._common.range_parser import (
    RangeError,
)
from pyxel_mcp.observe._harnesses._common.range_parser import (
    resolve_frames as _resolve_frames,
)
from pyxel_mcp.observe._harnesses._common.script_loader import (
    load_script_module,
    resolve_script_path,
)
from pyxel_mcp.observe._harnesses._common.snapshot_kinds import (
    screen_grid as _sg_kind,
)
from pyxel_mcp.observe._harnesses._common.snapshot_kinds import (
    screen_image as _si_kind,
)
from pyxel_mcp.observe._harnesses._common.snapshot_kinds import (
    state as _state_kind,
)
from pyxel_mcp.observe._harnesses._common.snapshot_kinds import (
    video as _video_kind,
)
from pyxel_mcp.observe._harnesses._common.until_condition import (
    UntilCondition,
    UntilError,
)


class _ValidationFailed(Exception):
    """Raised internally when payload validation fails; carries the error dict."""

    def __init__(self, err: dict):
        self.err = err


def _empty_result(*, exit_status: str = "ok", errors: list | None = None) -> dict:
    errs = errors or []
    return {
        "ok": _is_ok(exit_status, errs),
        "snapshots": [],
        "exit_status": exit_status,
        "frame_count": 0,
        "elapsed_seconds": 0.0,
        "log": "",
        "seeded": False,
        "until_met": None,
        "errors": errs,
    }


def _is_ok(exit_status: str, errors: list) -> bool:
    """Successful completion includes the frame cap, until, and explicit quit."""
    return len(errors) == 0 and exit_status == "ok"


def _substitute_output_pattern(pattern: str, frame: int) -> str:
    """Replace {frame} with 5-digit zero-padded integer; reject other tokens.

    Raises ValueError for format specifiers ({frame:03d}) or unknown tokens ({foo}).
    """
    if re.search(r"\{[^}]*:[^}]*\}", pattern):
        raise ValueError(
            "output_pattern: format specifiers like {frame:03d} not supported"
        )
    if "{frame}" not in pattern:
        raise ValueError(f"output_pattern must contain literal {{frame}}: {pattern!r}")
    other = re.search(r"\{(?!frame\b)[^}]+\}", pattern)
    if other:
        raise ValueError(f"output_pattern: unknown token {other.group(0)}")
    return pattern.replace("{frame}", f"{frame:05d}")


def _expand_multi_frame_snapshots(
    snaps: list[dict],
    total_frames: int,
) -> tuple[list[dict], list[str]]:
    """Expand any multi-frame snapshot (using `frames`) into N single-frame dicts.

    Returns (expanded_snaps, pending_warnings).
    Raises _ValidationFailed if any snapshot has structural errors.
    """
    expanded: list[dict] = []
    warnings: list[str] = []

    for i, snap in enumerate(snaps):
        if "frames" not in snap:
            expanded.append(snap)
            continue
        kind = snap["kind"]
        if kind == "screen_image":
            try:
                _substitute_output_pattern(snap["output_pattern"], 0)
            except ValueError as exc:
                raise _ValidationFailed(make_validation_error(str(exc))) from exc

        # Resolve frames list
        try:
            resolved, was_normalized = _resolve_frames(
                snap["frames"], total_frames=total_frames
            )
        except RangeError as e:
            raise _ValidationFailed(
                make_validation_error(f"`snapshots[{i}].frames` error: {e}")
            )

        if was_normalized:
            warnings.append(
                f"snapshots[{i}]: frames list was sorted and/or deduplicated"
            )

        # Build one derived snapshot per resolved frame
        for f in resolved:
            derived = {
                k: v for k, v in snap.items() if k not in ("frames", "output_pattern")
            }
            derived["frame"] = f
            if kind == "screen_image":
                derived["output"] = _substitute_output_pattern(
                    snap["output_pattern"], f
                )
            expanded.append(derived)

    return expanded, warnings


def _validate(payload: dict[str, Any]) -> tuple[Any, ...]:
    """Apply the shared input contract, then resolve runtime-dependent values."""
    try:
        request = RunRequest.model_validate(payload)
    except ModelValidationError as exc:
        raise _ValidationFailed(make_validation_error(str(exc))) from exc

    try:
        path = resolve_script_path(request.script)
    except FileNotFoundError as exc:
        raise _ValidationFailed(
            make_validation_error(str(exc), path=request.script)
        ) from exc

    until_condition = None
    if request.until is not None:
        try:
            if not request.until.strip():
                raise ValueError("`until` must be a non-empty expression")
            until_condition = UntilCondition(request.until)
        except (SyntaxError, ValueError) as exc:
            raise _ValidationFailed(make_validation_error(str(exc))) from exc

    raw_snapshots = [snap.model_dump(exclude_none=True) for snap in request.snapshots]
    for i, snap in enumerate(raw_snapshots):
        output_field = "output_pattern" if "frames" in snap else "output"
        if snap["kind"] in ("screen_image", "video"):
            error = absolute_path_error(
                snap.get(output_field), f"snapshots[{i}].{output_field}"
            )
            if error:
                raise _ValidationFailed(make_validation_error(error))
        if snap["kind"] == "video":
            if Path(snap["output"]).suffix.lower() not in (".gif", ".mp4"):
                raise _ValidationFailed(
                    make_validation_error("video output extension must be .gif or .mp4")
                )
            if snap["end_frame"] > request.frames:
                raise _ValidationFailed(
                    make_validation_error(
                        f"video end_frame must be <= frames ({request.frames})"
                    )
                )
        elif isinstance(snap.get("frame"), int) and snap["frame"] >= request.frames:
            raise _ValidationFailed(
                make_validation_error(
                    f"snapshot frame must be < frames ({request.frames})"
                )
            )

    snapshots, warnings = _expand_multi_frame_snapshots(raw_snapshots, request.frames)
    try:
        scheduler = InputScheduler(request.inputs)
    except ValidationError as exc:
        raise _ValidationFailed(make_validation_error(str(exc))) from exc

    return (
        path,
        request.frames,
        request.random_seed,
        snapshots,
        scheduler,
        warnings,
        request.stall_window_frames,
        until_condition,
    )


def _capture_screen_as_pil() -> Image.Image:
    """Return the current pyxel.screen as an RGB PIL image.

    Reads the palette indices straight from `pyxel.screen.data_ptr()` and maps
    them through `pyxel.colors`, so video capture never touches the disk.
    """
    import numpy as np
    import pyxel

    w, h = pyxel.width, pyxel.height
    arr = np.frombuffer(
        pyxel.screen.data_ptr(),
        dtype=np.uint8,
        count=w * h,
    ).reshape((h, w))

    # Build the palette LUT — pad to 256 entries so direct indexing is safe
    # even if a script writes an out-of-palette value (defensive).
    lut = np.zeros((256, 3), dtype=np.uint8)
    for i, c in enumerate(pyxel.colors):
        lut[i, 0] = (c >> 16) & 0xFF
        lut[i, 1] = (c >> 8) & 0xFF
        lut[i, 2] = c & 0xFF

    rgb = lut[arr]
    return Image.fromarray(rgb, "RGB")


def _grid_signature(grid: list) -> tuple:
    """Turn a screen_grid into a nested tuple that compares by value."""
    return tuple(tuple(row) for row in grid)


def _is_asset_load_error(tb_text: str) -> bool:
    """Classify a traceback as an asset-load failure by its message.

    Pyxel raises a plain Exception reading "Failed to open file '<path>'";
    Python's FileNotFoundError and "could not open" are accepted as well. A
    script raising a custom error with the same words is misclassified, so
    revisit this if Pyxel ever exposes a typed asset error.
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
    and drives update/draw inside the intercepted pyxel.run() call, preserving
    the script's active stack and resources throughout observation.
    Errors are caught per-phase and reported in the `errors` list rather than
    raised, so callers always receive a well-formed result dict.

    The result includes `ok: bool` — True iff `len(errors) == 0` AND
    `exit_status == "ok"`. A stalled run still returns diagnostic data, but
    `ok` is false because the requested frame budget was not reached.
    """
    try:
        (
            path,
            frames,
            random_seed,
            snapshots,
            scheduler,
            pending_warnings,
            stall_window,
            until_condition,
        ) = _validate(payload)
    except _ValidationFailed as vf:
        return _empty_result(exit_status="invalid", errors=[vf.err])

    started = time.monotonic()
    errors: list[dict] = []
    seeded = False
    frame_count = 0
    exit_status = "ok"
    # Stays None until `until` has actually been evaluated once.
    until_met: bool | None = None

    # Pre-loop: split snapshots into per-frame captures vs. video accumulators.
    video_accumulators: list[_video_kind.VideoAccumulator] = []
    single_frame_snaps: list[dict] = []
    for snap in snapshots:
        if snap["kind"] == "video":
            try:
                video_accumulators.append(_video_kind.VideoAccumulator(snap))
            except Exception as e:
                return _empty_result(
                    exit_status="crashed",
                    errors=[
                        make_error(
                            ErrorPhase.ARTIFACT,
                            f"video setup failed: {e}",
                            path=snap.get("output"),
                            capture_traceback=True,
                        )
                    ],
                )
        else:
            single_frame_snaps.append(snap)
    snapshot_results: list[dict] = []

    # `"frame": "end"` snapshots are deferred until the last completed frame
    # is known, so they are excluded from the per-frame dispatch loop below.
    end_snaps = [s for s in single_frame_snaps if s.get("frame") == "end"]
    if end_snaps:
        single_frame_snaps = [s for s in single_frame_snaps if s.get("frame") != "end"]

    # Stall detection setup. We track the rolling buffer here so we can also
    # warn (after the loop) if the agent set stall_window_frames but did not
    # schedule any state or screen_grid snapshots — in that case we have no
    # signal to compare against and cannot detect stalls.
    has_state_snap = any(s["kind"] == "state" for s in single_frame_snaps)
    has_grid_snap = any(s["kind"] == "screen_grid" for s in single_frame_snaps)
    stall_active = stall_window is not None and (has_state_snap or has_grid_snap)
    state_buffer: list[dict] = []
    grid_buffer: list[tuple] = []

    log_buf = StringIO()
    # Each entry is (resolved request, captured data, deferred capture error).
    # Only one completed frame is retained, regardless of the frame budget.
    end_candidates: list[tuple[dict, Any, dict | None]] = []

    def remember_end_frame(
        frame: int, state: PreLoopState, module: Any, image: Image.Image | None
    ) -> list[tuple[dict, Any, dict | None]]:
        candidates = []
        for snap in end_snaps:
            resolved = {**snap, "frame": frame}
            kind = resolved["kind"]
            try:
                if kind == "screen_image":
                    if image is None:
                        image = _capture_screen_as_pil()
                    captured = image
                elif kind == "screen_grid":
                    captured = _sg_kind.capture(resolved)
                else:
                    captured = _state_kind.capture(
                        resolved,
                        app_instance=state.app_instance,
                        module=module,
                        stored_only=True,
                    )
                candidates.append((resolved, captured, None))
            except Exception as exc:
                # A property may be unavailable until a later frame. Only an
                # error on the selected final completed frame is reported.
                error = make_error(
                    ErrorPhase.ARTIFACT,
                    f"{kind} end snapshot failed: {exc}",
                    path=resolved.get("output"),
                    frame=frame,
                    capture_traceback=True,
                )
                candidates.append((resolved, None, error))
        return candidates

    def drive_frames(state: PreLoopState) -> None:
        nonlocal frame_count, exit_status, until_met, end_candidates
        import pyxel

        imported_module = sys.modules["__main__"]

        # until expressions resolve names on the App instance when one
        # exists, else on the module (same fallback as state snapshots).
        until_target = (
            state.app_instance if state.app_instance is not None else imported_module
        )

        # Phase 3: drive the update/draw loop
        for f in range(frames):
            try:
                pyxel.frame_count = f
                scheduler.advance_to_frame(f)
                scheduler.apply_to_pyxel()
                state.update_callback()
                if state.quit_requested:
                    raise QuitRequested
                state.draw_callback()
                if state.quit_requested:
                    raise QuitRequested
                frame_count = f + 1
            except Exception as e:
                errors.append(
                    make_error(
                        ErrorPhase.GAME_LOOP,
                        str(e),
                        frame=f,
                        capture_traceback=True,
                    )
                )
                exit_status = "crashed"
                frame_count = f
                break

            # Single-frame snapshot dispatch
            captured_state_this_frame: dict | None = None
            captured_grid_this_frame: list | None = None
            artifact_failed = False
            for snap in single_frame_snaps:
                if snap.get("frame") != f:
                    continue
                kind = snap["kind"]
                try:
                    if kind == "screen_image":
                        snapshot_results.append(_si_kind.capture(snap))
                    elif kind == "screen_grid":
                        res = _sg_kind.capture(snap)
                        snapshot_results.append(res)
                        captured_grid_this_frame = res.get("grid")
                    elif kind == "state":
                        res = _state_kind.capture(
                            snap,
                            app_instance=state.app_instance,
                            module=imported_module,
                        )
                        snapshot_results.append(res)
                        captured_state_this_frame = res.get("values")
                except (Exception, QuitRequested) as e:
                    message = (
                        "pyxel.quit() interrupted the observation"
                        if isinstance(e, QuitRequested)
                        else str(e)
                    )
                    errors.append(
                        make_error(
                            ErrorPhase.ARTIFACT,
                            f"{kind} snapshot failed: {message}",
                            path=snap.get("output"),
                            frame=f,
                            capture_traceback=True,
                        )
                    )
                    exit_status = "crashed"
                    artifact_failed = True
                    break

            if artifact_failed:
                break

            # Video frame accumulation
            img = None
            if video_accumulators:
                try:
                    img = _capture_screen_as_pil()
                    for accum in video_accumulators:
                        accum.add_frame(f, img)
                except Exception as e:
                    errors.append(
                        make_error(
                            ErrorPhase.ARTIFACT,
                            f"video frame capture failed: {e}",
                            frame=f,
                            capture_traceback=True,
                        )
                    )
                    exit_status = "crashed"
                    break

            # Keep only the most recent completed frame for deferred snapshots.
            # A later update/draw may change state or pixels and then quit.
            end_candidates = remember_end_frame(f, state, imported_module, img)

            # Until condition: evaluated after the frame completes, so
            # the stop frame's draw and snapshots are already done.
            if until_condition is not None:
                try:
                    met = until_condition.evaluate(until_target)
                except (UntilError, QuitRequested) as e:
                    message = (
                        "pyxel.quit() interrupted until evaluation"
                        if isinstance(e, QuitRequested)
                        else str(e)
                    )
                    errors.append(
                        make_error(
                            ErrorPhase.UNTIL,
                            message,
                            frame=f,
                        )
                    )
                    exit_status = "crashed"
                    break
                if until_condition.pending_warning:
                    log_buf.write(
                        f"[pyxel-mcp] warning: {until_condition.pending_warning}\n"
                    )
                    until_condition.pending_warning = None
                until_met = met
                if met:
                    break

            # Stall detection: maintain rolling buffer of the most
            # recent N captured state-values and grid-signatures. If at
            # least one buffer is full and every entry is identical,
            # the run has not advanced for N consecutive frames despite
            # scheduled inputs — break early and surface "stalled".
            if stall_active:
                if captured_state_this_frame is not None:
                    state_buffer.append(captured_state_this_frame)
                    if len(state_buffer) > stall_window:
                        state_buffer.pop(0)
                if captured_grid_this_frame is not None:
                    grid_buffer.append(_grid_signature(captured_grid_this_frame))
                    if len(grid_buffer) > stall_window:
                        grid_buffer.pop(0)

                if (
                    len(state_buffer) == stall_window
                    and all(v == state_buffer[0] for v in state_buffer[1:])
                ) or (
                    len(grid_buffer) == stall_window
                    and all(g == grid_buffer[0] for g in grid_buffer[1:])
                ):
                    exit_status = "stalled"
                    break

            # Observe the completed draw before flip(): presentation
            # may rotate or clear the back buffer. Flip only when a
            # following frame needs fresh input-edge state. Leaving the
            # final frame unflipped also keeps `frame: "end"` exact.
            if f + 1 < frames:
                try:
                    pyxel.flip()
                except Exception as e:
                    errors.append(
                        make_error(
                            ErrorPhase.GAME_LOOP,
                            str(e),
                            frame=f,
                            capture_traceback=True,
                        )
                    )
                    exit_status = "crashed"
                    break

    def observe_run(state: PreLoopState) -> None:
        nonlocal exit_status
        stopped_by_quit = False
        try:
            drive_frames(state)
        except QuitRequested:
            stopped_by_quit = True
            log_buf.write(
                "[pyxel-mcp] script called pyxel.quit(); stopped after "
                f"{frame_count} completed frame(s).\n"
            )

        # Save end snapshots before the script's enclosing finally/with blocks
        # unwind. Cached data excludes any partially executed quit frame.
        if exit_status in ("ok", "stalled"):
            for resolved, captured, error in end_candidates:
                ordinary_state = resolved["kind"] == "state" and not stopped_by_quit
                if error is not None and not ordinary_state:
                    errors.append(error)
                    exit_status = "crashed"
                    break
                try:
                    if ordinary_state:
                        snapshot_results.append(
                            _state_kind.capture(
                                resolved,
                                app_instance=state.app_instance,
                                module=sys.modules["__main__"],
                            )
                        )
                    elif resolved["kind"] == "screen_image":
                        snapshot_results.append(
                            _si_kind.capture(resolved, image=captured)
                        )
                    else:
                        snapshot_results.append(captured)
                except (Exception, QuitRequested) as exc:
                    message = (
                        "pyxel.quit() interrupted the observation"
                        if isinstance(exc, QuitRequested)
                        else str(exc)
                    )
                    errors.append(
                        make_error(
                            ErrorPhase.ARTIFACT,
                            f"{resolved['kind']} end snapshot failed: {message}",
                            path=resolved.get("output"),
                            frame=resolved["frame"],
                            capture_traceback=True,
                        )
                    )
                    exit_status = "crashed"
                    break

    # Run the driver on the script's pyxel.run() stack. The patcher stops script
    # execution after observation, so post-run statements cannot alter the run.
    with (
        headless_pyxel(random_seed=random_seed, on_run=observe_run) as state,
        contextlib.redirect_stdout(log_buf),
        contextlib.redirect_stderr(log_buf),
    ):
        for warning in pending_warnings:
            log_buf.write(f"[pyxel-mcp] warning: {warning}\n")
        if stall_window is not None and not stall_active:
            log_buf.write(
                "[pyxel-mcp] warning: stall_window_frames is set but no "
                "`state` or `screen_grid` snapshot is scheduled; "
                "stall detection has no signal to compare and is disabled.\n"
            )
        if random_seed is not None:
            import random as _random

            _random.seed(random_seed)
            seeded = True

        try:
            load_script_module(path)
        except ObservationFinished:
            pass
        except QuitRequested:
            # Explicit quit before pyxel.run(), or during enclosing cleanup.
            log_buf.write(
                "[pyxel-mcp] script called pyxel.quit(); stopped after "
                f"{frame_count} completed frame(s).\n"
            )
        except Exception as exc:
            if state.run_called:
                phase = ErrorPhase.SCRIPT_EXIT
                message = f"script cleanup failed: {exc}"
            elif isinstance(exc, FileNotFoundError) or _is_asset_load_error(
                _tb.format_exc()
            ):
                phase = ErrorPhase.ASSET_LOAD
                message = str(exc)
            else:
                phase = ErrorPhase.SCRIPT_IMPORT
                message = str(exc)
            errors.append(
                make_error(phase, message, path=str(path), capture_traceback=True)
            )
            exit_status = "crashed"

        if not errors and not state.quit_requested:
            try:
                state.require_run_called()
            except RunNotCalledError as exc:
                errors.append(make_error(ErrorPhase.SCRIPT_IMPORT, str(exc)))
                exit_status = "crashed"

        # Post-loop: encode all video accumulators (partial videos are useful for debugging)
        for accum in video_accumulators:
            if not accum.frames:
                accum.close()
                log_buf.write(
                    "[pyxel-mcp] warning: video skipped because the run ended "
                    "before any frames in its capture range were recorded: "
                    f"{accum.requested_output}\n"
                )
                continue
            try:
                snapshot_results.append(accum.encode())
            except Exception as e:
                errors.append(
                    make_error(
                        ErrorPhase.ARTIFACT,
                        f"video encode failed: {e}",
                        path=str(accum.requested_output),
                        frame=frame_count - 1 if frame_count else None,
                        capture_traceback=True,
                    )
                )
                exit_status = "crashed"

    # redirect_stdout/stderr context is now closed — real stdout is restored
    log_text = log_buf.getvalue()

    elapsed = time.monotonic() - started
    return {
        "ok": _is_ok(exit_status, errors),
        "snapshots": snapshot_results,
        "exit_status": exit_status,
        "frame_count": frame_count,
        "elapsed_seconds": elapsed,
        "log": log_text,
        "seeded": seeded,
        "until_met": until_met,
        "errors": errors,
    }
