"""run(script, frames, ...) — dynamic execution driver (spec §6)."""
from __future__ import annotations
import contextlib
import os
import tempfile
import time
import traceback as _tb
from io import StringIO
from pathlib import Path
from typing import Any

from PIL import Image

from pyxel_mcp._harnesses._common.error_capture import (
    make_error, make_validation_error, ErrorPhase,
)
from pyxel_mcp._harnesses._common.input_scheduler import InputScheduler, ValidationError
from pyxel_mcp._harnesses._common.pyxel_patcher import headless_pyxel, RunNotCalledError
from pyxel_mcp._harnesses._common.range_parser import resolve_frames as _resolve_frames, RangeError
from pyxel_mcp._harnesses._common.script_loader import resolve_script_path, load_script_module
from pyxel_mcp._harnesses._common.snapshot_kinds import (
    screen_image as _si_kind,
    screen_grid as _sg_kind,
    state as _state_kind,
    layout as _layout_kind,
    video as _video_kind,
)


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


_VALID_SNAPSHOT_KINDS = {"screen_image", "screen_grid", "state", "layout", "video"}


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
        has_frame = "frame" in snap
        has_frames = "frames" in snap
        has_output = "output" in snap
        has_pattern = "output_pattern" in snap

        # Mutual exclusivity: frame + frames
        if has_frame and has_frames:
            raise _ValidationFailed(make_validation_error(
                f"`snapshots[{i}]` must not have both `frame` and `frames`"
            ))

        # Mutual exclusivity: output + output_pattern
        if has_output and has_pattern:
            raise _ValidationFailed(make_validation_error(
                f"`snapshots[{i}]` must not have both `output` and `output_pattern`"
            ))

        kind = snap.get("kind")

        if not has_frames:
            # Single-frame snapshot (or video): pass through, but reject
            # output_pattern in single-frame mode per spec §6.6.
            if has_pattern and kind != "video":
                raise _ValidationFailed(make_validation_error(
                    f"`snapshots[{i}]` single-frame mode requires `output`, not `output_pattern`"
                ))
            expanded.append(snap)
            continue

        # Multi-frame snapshot. (video+frames was already rejected in the
        # first-pass shape validation; non-video kinds reach here.)

        # screen_image multi-frame requires output_pattern (not output)
        if kind == "screen_image":
            if not has_pattern:
                raise _ValidationFailed(make_validation_error(
                    f"`snapshots[{i}]` multi-frame screen_image requires `output_pattern`"
                ))
            if "{frame}" not in snap["output_pattern"]:
                raise _ValidationFailed(make_validation_error(
                    f"`snapshots[{i}].output_pattern` must contain {{frame}} token"
                ))

        # Resolve frames list
        try:
            resolved, was_normalized = _resolve_frames(snap["frames"], total_frames=total_frames)
        except RangeError as e:
            raise _ValidationFailed(make_validation_error(
                f"`snapshots[{i}].frames` error: {e}"
            ))

        if was_normalized:
            warnings.append(
                f"snapshots[{i}]: frames list was sorted and/or deduplicated"
            )

        # Build one derived snapshot per resolved frame
        for f in resolved:
            derived = {k: v for k, v in snap.items() if k not in ("frames", "output_pattern")}
            derived["frame"] = f
            if kind == "screen_image":
                derived["output"] = snap["output_pattern"].replace("{frame}", f"{f:05d}")
            expanded.append(derived)

    return expanded, warnings


def _validate(payload: dict[str, Any]) -> tuple[Any, ...]:
    """Validate payload and return (script_path, frames, random_seed, snapshots, scheduler, warnings).

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

    raw_snapshots = payload.get("snapshots", [])
    if not isinstance(raw_snapshots, list):
        raise _ValidationFailed(make_validation_error("`snapshots` must be a list"))

    # First pass: shape validation (kind, video range/extension)
    for i, snap in enumerate(raw_snapshots):
        if not isinstance(snap, dict):
            raise _ValidationFailed(make_validation_error(
                f"`snapshots[{i}]` must be a dict"
            ))
        kind = snap.get("kind")
        if kind not in _VALID_SNAPSHOT_KINDS:
            raise _ValidationFailed(make_validation_error(
                f"`snapshots[{i}].kind` must be one of {sorted(_VALID_SNAPSHOT_KINDS)}, got: {kind!r}"
            ))
        if kind == "video":
            # video uses start_frame/end_frame, not the multi-frame `frames` field
            if "frames" in snap:
                raise _ValidationFailed(make_validation_error(
                    f"`snapshots[{i}]` video kind does not support `frames`; use `start_frame`/`end_frame`"
                ))
            # Validate extension early without keeping the instance.
            out = snap.get("output", "")
            ext = Path(str(out)).suffix.lower()
            if ext not in (".gif", ".mp4"):
                raise _ValidationFailed(make_validation_error(
                    f"`snapshots[{i}]` video output extension must be .gif or .mp4, got: {ext or '(none)'}"
                ))
            # Validate video frame range (spec §6.4.5).
            start = snap.get("start_frame")
            end = snap.get("end_frame")
            if not isinstance(start, int) or start < 0:
                raise _ValidationFailed(make_validation_error(
                    f"`snapshots[{i}].start_frame` must be int >= 0"
                ))
            if not isinstance(end, int) or end > frames:
                raise _ValidationFailed(make_validation_error(
                    f"`snapshots[{i}].end_frame` must be int <= frames ({frames})"
                ))
            if start >= end:
                raise _ValidationFailed(make_validation_error(
                    f"`snapshots[{i}]` start_frame ({start}) must be < end_frame ({end})"
                ))

    # Pre-expansion: resolve `frames` lists into single-frame snapshots
    snapshots, pending_warnings = _expand_multi_frame_snapshots(raw_snapshots, frames)

    # Second pass: frame-bound validation on expanded single-frame snapshots
    for i, snap in enumerate(snapshots):
        kind = snap.get("kind")
        if kind != "video":
            frame = snap.get("frame")
            if frame is not None:
                if not isinstance(frame, int) or frame < 0 or frame >= frames:
                    raise _ValidationFailed(make_validation_error(
                        f"`snapshots[{i}].frame` must satisfy 0 <= frame < frames ({frames}), got: {frame!r}"
                    ))

    inputs = payload.get("inputs", [])
    if not isinstance(inputs, list):
        raise _ValidationFailed(make_validation_error("`inputs` must be a list"))
    try:
        scheduler = InputScheduler(inputs)
    except ValidationError as e:
        raise _ValidationFailed(make_validation_error(str(e)))

    return path, frames, random_seed, snapshots, scheduler, pending_warnings


def _capture_screen_as_pil() -> Image.Image:
    """Return current pyxel.screen contents as a PIL.Image (RGB mode).

    Uses pyxel.screen.save() to write a temp PNG and reads it back via PIL.
    Reuses the established pyxel.screen.save pattern from screen_image.py.
    """
    import pyxel

    fd, tmp_path = tempfile.mkstemp(suffix=".png")
    os.close(fd)
    try:
        # pyxel.screen.save appends .png automatically; strip it to avoid double extension.
        base = tmp_path[:-4]
        pyxel.screen.save(base, 1)  # scale=1; VideoAccumulator handles its own scaling
        img = Image.open(tmp_path)
        img.load()  # force-read before deleting the underlying file
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
    return img


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
        path, frames, random_seed, snapshots, scheduler, pending_warnings = _validate(payload)
    except _ValidationFailed as vf:
        return _empty_result(exit_status="invalid", errors=[vf.err])

    started = time.monotonic()
    errors: list[dict] = []
    seeded = False
    frame_count = 0
    exit_status = "ok"

    # Pre-loop: split snapshots into per-frame captures vs. video accumulators.
    video_accumulators: list[_video_kind.VideoAccumulator] = []
    single_frame_snaps: list[dict] = []
    for snap in snapshots:
        if snap["kind"] == "video":
            video_accumulators.append(_video_kind.VideoAccumulator(snap))
        else:
            single_frame_snaps.append(snap)
    snapshot_results: list[dict] = []

    # Capture stdout+stderr from the user script into log_buf.
    # The real stdout is reserved for the JSON result written by main.py,
    # so the redirect must be closed before run() returns.
    log_buf = StringIO()
    with headless_pyxel() as state:
        with contextlib.redirect_stdout(log_buf), contextlib.redirect_stderr(log_buf):
            # Write any validation warnings collected during pre-expansion
            for w in pending_warnings:
                log_buf.write(f"[pyxel-mcp] warning: {w}\n")

            # Phase 1: import script (pyxel.run is intercepted by headless_pyxel)
            imported_module = None
            try:
                imported_module = load_script_module(path)
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
                        scheduler.advance_to_frame(f)
                        scheduler.apply_to_pyxel()
                        state.update_callback()
                        state.draw_callback()
                        # flip() commits this frame's input state so the next
                        # apply_to_pyxel() writes set_btn(K, False) onto a fresh
                        # slate. Without it, Pyxel's binary holds the prior True.
                        pyxel.flip()
                        frame_count = f + 1
                    except Exception as e:
                        errors.append(make_error(
                            ErrorPhase.GAME_LOOP, str(e), frame=f, capture_traceback=True,
                        ))
                        exit_status = "crashed"
                        frame_count = f
                        break

                    # Single-frame snapshot dispatch
                    for snap in single_frame_snaps:
                        if snap.get("frame") != f:
                            continue
                        kind = snap["kind"]
                        if kind == "screen_image":
                            snapshot_results.append(_si_kind.capture(snap))
                        elif kind == "screen_grid":
                            snapshot_results.append(_sg_kind.capture(snap))
                        elif kind == "state":
                            snapshot_results.append(_state_kind.capture(
                                snap,
                                app_instance=state.app_instance,
                                module=imported_module,
                            ))
                        elif kind == "layout":
                            snapshot_results.append(_layout_kind.capture(snap))

                    # Video frame accumulation
                    if video_accumulators:
                        img = _capture_screen_as_pil()
                        for accum in video_accumulators:
                            accum.add_frame(f, img)

            # Post-loop: encode all video accumulators (partial videos are useful for debugging)
            for accum in video_accumulators:
                snapshot_results.append(accum.encode())

    # redirect_stdout/stderr context is now closed — real stdout is restored
    log_text = log_buf.getvalue()

    elapsed = time.monotonic() - started
    return {
        "snapshots": snapshot_results,
        "assertions": [],
        "exit_status": exit_status,
        "frame_count": frame_count,
        "elapsed_seconds": elapsed,
        "log": log_text,
        "seeded": seeded,
        "errors": errors,
    }
