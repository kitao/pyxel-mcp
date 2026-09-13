"""Pre-loop checkpoint shared by the script-loading read_* tools.

Validates `script`, enters headless Pyxel, loads the module, and requires the
`pyxel.run` call, so read_palette, read_image, read_tilemap, and read_audio
report the same error phases.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any

from pyxel_mcp.observe._harnesses._common.error_capture import (
    ErrorPhase,
    make_error,
    make_validation_error,
)
from pyxel_mcp.observe._harnesses._common.pyxel_patcher import (
    RunNotCalledError,
    headless_pyxel,
)
from pyxel_mcp.observe._harnesses._common.script_loader import (
    load_script_module,
    resolve_script_path,
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
        raise PreloopFailed(
            empty_factory(make_validation_error("missing or non-str `script`"))
        )

    try:
        path = resolve_script_path(script)
    except FileNotFoundError as e:
        raise PreloopFailed(empty_factory(make_validation_error(str(e), path=script)))

    with headless_pyxel() as state:
        try:
            load_script_module(path)
            state.require_run_called()
        except RunNotCalledError as e:
            raise PreloopFailed(
                empty_factory(make_error(ErrorPhase.SCRIPT_IMPORT, str(e)))
            )
        except Exception as e:
            raise PreloopFailed(
                empty_factory(
                    make_error(ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=True)
                )
            )

        yield state
