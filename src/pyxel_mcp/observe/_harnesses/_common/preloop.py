"""Pre-loop checkpoint helper used by all script-loading read_* tools.

Centralises the script validation + headless_pyxel + load_script_module +
require_run_called dance shared by read_palette, read_image,
read_animation, read_tilemap, and read_audio. Each of those tools
previously copy-pasted the same ~12 lines of try/except plumbing; consolidating
here keeps the error mapping and phase tagging consistent across tools.
"""
from __future__ import annotations
from contextlib import contextmanager
from typing import Any, Callable, Iterator

from pyxel_mcp.observe._harnesses._common.error_capture import (
    make_error, make_validation_error, ErrorPhase,
)
from pyxel_mcp.observe._harnesses._common.pyxel_patcher import headless_pyxel, RunNotCalledError
from pyxel_mcp.observe._harnesses._common.script_loader import (
    resolve_script_path, load_script_module,
)


class PreloopFailed(Exception):
    """Raised by `run_to_preloop` when the preamble (validation, script load,
    or `pyxel.run` requirement) fails. Carries an empty-shaped result dict
    that the caller can `return` directly.
    """

    def __init__(self, result: dict):
        self.result = result


@contextmanager
def run_to_preloop(
    payload: dict[str, Any],
    *,
    empty_factory: Callable[[dict], dict],
) -> Iterator[Any]:
    """Validate `script`, enter headless_pyxel, load the script, and yield the
    pyxel state object so the body can perform its analysis at the pre-loop
    checkpoint.

    On any failure (missing/invalid `script`, file not found, script crash on
    import, missing `pyxel.run` call), raises `PreloopFailed` carrying an
    empty-shaped result dict built via `empty_factory(error_dict)`. Callers
    typically `try: ... except PreloopFailed as f: return f.result`.

    `empty_factory` receives a single ToolError dict and must return the
    tool's empty/error shape (with `errors=[error]` and `ok=False`).
    """
    script = payload.get("script")
    if not isinstance(script, str):
        raise PreloopFailed(empty_factory(
            make_validation_error("missing or non-str `script`")
        ))

    try:
        path = resolve_script_path(script)
    except FileNotFoundError as e:
        raise PreloopFailed(empty_factory(
            make_validation_error(str(e), path=script)
        ))

    with headless_pyxel() as state:
        try:
            load_script_module(path)
            state.require_run_called()
        except RunNotCalledError as e:
            raise PreloopFailed(empty_factory(
                make_error(ErrorPhase.SCRIPT_IMPORT, str(e))
            ))
        except Exception as e:
            raise PreloopFailed(empty_factory(
                make_error(ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=True)
            ))

        yield state
