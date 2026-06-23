"""Headless Pyxel + run-intercept (spec §5.1, §5.7)."""
from __future__ import annotations
import contextlib
import os
from dataclasses import dataclass
from typing import Callable


class RunNotCalledError(RuntimeError):
    """Script did not invoke pyxel.run during import."""


@dataclass
class PreLoopState:
    """Captured at the pre-loop checkpoint (spec §5.7)."""
    update_callback: Callable | None = None
    draw_callback: Callable | None = None
    app_instance: object | None = None  # update_callback.__self__ if bound; else None
    run_called: bool = False

    def require_run_called(self) -> None:
        if not self.run_called:
            raise RunNotCalledError("script did not call pyxel.run during import")


@contextlib.contextmanager
def headless_pyxel():
    """Context manager: sets SDL headless, intercepts pyxel.run, restores on exit.

    Yields a PreLoopState that the caller fills via the script's pyxel.run call.

    pyxel.init is also patched to inject headless=True and to silently skip
    re-initialization when Pyxel is already initialized (width > 0). The latter
    is relevant only in test processes that share a single Pyxel module state
    across multiple test cases; in production each tool call runs in its own
    subprocess (spec §5.1), so re-init cannot happen.
    """
    import pyxel
    state = PreLoopState()

    def _capture_run(update, draw, *args, **kwargs):
        state.update_callback = update
        state.draw_callback = draw
        state.app_instance = getattr(update, "__self__", None)
        state.run_called = True
        # Do NOT actually start the Pyxel loop.

    saved_run = pyxel.run
    saved_init = pyxel.init
    saved_video_env = os.environ.get("SDL_VIDEODRIVER")
    saved_audio_env = os.environ.get("SDL_AUDIODRIVER")
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    os.environ["SDL_AUDIODRIVER"] = "dummy"

    def _headless_init(*args, **kwargs):
        # Skip if already initialized; safe because each production invocation
        # runs in a fresh subprocess — only test processes share module state.
        if pyxel.width > 0:
            return
        kwargs["headless"] = True  # override: headless mode is mandatory in harness context
        # Pyxel's `flip()` sleeps to maintain the fps target; under harness
        # control the frame loop is driven externally (run.py), so Pyxel's
        # internal fps only governs flip() wait. Forcing a high fps makes
        # flip() near-instant and turns N-frame runs into <N/30 seconds rather
        # than real-time playback. Game logic that reads pyxel.frame_count is
        # unaffected (run.py sets it explicitly each iteration).
        kwargs["fps"] = 10000
        saved_init(*args, **kwargs)

    pyxel.init = _headless_init
    pyxel.run = _capture_run
    try:
        yield state
    finally:
        pyxel.run = saved_run
        pyxel.init = saved_init
        if saved_video_env is None:
            os.environ.pop("SDL_VIDEODRIVER", None)
        else:
            os.environ["SDL_VIDEODRIVER"] = saved_video_env
        if saved_audio_env is None:
            os.environ.pop("SDL_AUDIODRIVER", None)
        else:
            os.environ["SDL_AUDIODRIVER"] = saved_audio_env
