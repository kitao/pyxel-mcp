"""Headless Pyxel + run-intercept."""

from __future__ import annotations

import contextlib
import inspect
import os
import sys
from collections.abc import Callable
from dataclasses import dataclass


class RunNotCalledError(RuntimeError):
    """Script did not invoke pyxel.run during import."""


class ObservationFinished(BaseException):
    """The requested observation completed inside the script's pyxel.run call."""


class QuitRequested(BaseException):
    """The script requested an orderly end without terminating the harness."""


@dataclass
class PreLoopState:
    """Captured at the pre-loop checkpoint."""

    update_callback: Callable | None = None
    draw_callback: Callable | None = None
    app_instance: object | None = None  # update_callback.__self__ if bound; else None
    run_called: bool = False
    quit_requested: bool = False

    def require_run_called(self) -> None:
        if not self.run_called:
            raise RunNotCalledError("script did not call pyxel.run during import")


@contextlib.contextmanager
def headless_pyxel(
    *,
    random_seed: int | None = None,
    on_run: Callable[[PreLoopState], None] | None = None,
):
    """Context manager: sets SDL headless, intercepts pyxel.run, restores on exit.

    Yields a PreLoopState that the caller fills via the script's pyxel.run call.
    When on_run is provided, execute it synchronously at that call site and
    then raise ObservationFinished to stop the surrounding script. This keeps
    resources surrounding pyxel.run alive while the observation runs. Without
    on_run, only capture callbacks for callers that drive them separately.
    pyxel.quit raises QuitRequested instead of terminating the process.

    pyxel.init is also patched to inject headless=True and silently skip
    re-initialization when Pyxel is already initialized (width > 0). An
    optional RNG seed is applied before script import and again after init,
    because initialization may reset Pyxel's RNG. Re-init is relevant only in
    test processes that share Pyxel state; production calls use subprocesses.
    """
    import pyxel

    state = PreLoopState()

    if random_seed is not None:
        pyxel.rseed(random_seed)

    def _capture_run(update, draw, *args, **kwargs):
        if state.quit_requested:
            raise QuitRequested
        if on_run is not None and state.run_called:
            raise RuntimeError(
                "recursive or repeated pyxel.run calls are not supported"
            )
        state.update_callback = update
        state.draw_callback = draw
        state.app_instance = getattr(update, "__self__", None)
        state.run_called = True
        if on_run is not None:
            on_run(state)
            raise ObservationFinished

    def _request_quit():
        state.quit_requested = True
        raise QuitRequested

    saved_run = pyxel.run
    saved_init = pyxel.init
    saved_quit = pyxel.quit
    saved_video_env = os.environ.get("SDL_VIDEODRIVER")
    saved_audio_env = os.environ.get("SDL_AUDIODRIVER")
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    def _headless_init(*args, **kwargs):
        # Skip if already initialized; safe because each production invocation
        # runs in a fresh subprocess — only test processes share module state.
        if pyxel.width > 0:
            if random_seed is not None:
                pyxel.rseed(random_seed)
            return
        # Bind before overriding so positional fps/headless arguments do not
        # conflict with injected keyword arguments.
        init_args = inspect.signature(saved_init).bind(*args, **kwargs)
        init_args.arguments["headless"] = True
        # Pyxel's `flip()` sleeps to maintain the fps target; under harness
        # control the frame loop is driven externally (run.py), so Pyxel's
        # internal fps only governs flip() wait. Forcing a high fps makes
        # flip() near-instant and turns N-frame runs into <N/30 seconds rather
        # than real-time playback. Game logic that reads pyxel.frame_count is
        # unaffected (run.py sets it explicitly each iteration).
        init_args.arguments["fps"] = 10000
        # pyxel.init chdirs to the directory of the file that called it. Seen
        # from Pyxel that file is this wrapper, so redo the move for the real
        # caller, exactly where `python game.py` would have ended up.
        caller_dir = os.path.dirname(sys._getframe(1).f_code.co_filename) or "."
        try:
            saved_init(*init_args.args, **init_args.kwargs)
        finally:
            os.chdir(caller_dir)
        if random_seed is not None:
            pyxel.rseed(random_seed)

    pyxel.init = _headless_init
    pyxel.run = _capture_run
    pyxel.quit = _request_quit
    try:
        yield state
    finally:
        pyxel.run = saved_run
        pyxel.init = saved_init
        pyxel.quit = saved_quit
        if saved_video_env is None:
            os.environ.pop("SDL_VIDEODRIVER", None)
        else:
            os.environ["SDL_VIDEODRIVER"] = saved_video_env
        if saved_audio_env is None:
            os.environ.pop("SDL_AUDIODRIVER", None)
        else:
            os.environ["SDL_AUDIODRIVER"] = saved_audio_env
