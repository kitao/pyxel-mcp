"""Common headless init patch for all harnesses."""

import os
import runpy
import sys

import pyxel


def patch_headless_init(script_path, transform_args=None):
    """Patch pyxel.init() for headless subprocess execution.

    Sets SDL_AUDIODRIVER=dummy to suppress audio output, enables headless
    mode, and fixes the working directory for runpy execution.

    Args:
        script_path: Absolute path to the user script.
        transform_args: Optional callable to transform positional args
            before passing to the original pyxel.init().
    """
    _original_init = pyxel.init

    def _headless_init(*args, **kwargs):
        os.environ["SDL_AUDIODRIVER"] = "dummy"
        kwargs["headless"] = True
        # Override fps for fast headless execution (bypass SDL_Delay throttle)
        if len(args) > 3:
            args = args[:3] + (1_000_000,) + args[4:]
        else:
            kwargs["fps"] = 1_000_000
        if transform_args:
            args = transform_args(args)
        _original_init(*args, **kwargs)
        # pyxel.init() chdir's to the caller's directory via inspect.stack(),
        # but under runpy that resolves to the harness, not the user script.
        os.chdir(os.path.dirname(script_path) or ".")

    pyxel.init = _headless_init


def run_script(script_path):
    """Execute a user script via runpy, suppressing SystemExit."""
    sys.path.insert(0, os.path.dirname(script_path))
    try:
        runpy.run_path(script_path, run_name="__main__")
    except SystemExit:
        pass


def setup_harness(script_path, transform_args=None):
    """Reset sys.argv and patch pyxel for headless mode.

    Call after parsing your own args but before run_script.

    Args:
        script_path: Absolute path to the user script.
        transform_args: Optional callable passed to patch_headless_init.
    """
    sys.argv = [script_path]
    patch_headless_init(script_path, transform_args)


def patch_game_loop(on_frame, on_show=None, pre_update=None):
    """Patch pyxel.run/show/flip with unified frame-based capture.

    Args:
        on_frame: Called each frame as on_frame(frame_count, draw).
            Return True to exit via os._exit(0).
        on_show: Called when pyxel.show() is invoked. If None,
            calls on_frame(0, lambda: None) instead.
        pre_update: Called before update() in run path and before
            on_frame in flip path. Use for input injection.
    """
    _original_run = pyxel.run
    _original_show = pyxel.show
    _original_flip = pyxel.flip

    def _patched_run(update, draw):
        def _wrapped_update():
            if pre_update:
                pre_update()
            update()
            if on_frame(pyxel.frame_count, draw):
                pyxel.quit()
                os._exit(0)
        _original_run(_wrapped_update, draw)

    def _patched_show():
        if on_show:
            on_show()
        else:
            on_frame(0, lambda: None)
        pyxel.quit()
        os._exit(0)

    def _patched_flip():
        _original_flip()
        if pre_update:
            pre_update()
        if on_frame(pyxel.frame_count, lambda: None):
            pyxel.quit()
            os._exit(0)

    pyxel.run = _patched_run
    pyxel.show = _patched_show
    pyxel.flip = _patched_flip


def noop_game_loop():
    """Patch run/show/flip to no-ops. For resource-only harnesses."""
    pyxel.run = lambda update, draw: None
    pyxel.show = lambda: None
    pyxel.flip = lambda: None
