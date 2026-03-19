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
