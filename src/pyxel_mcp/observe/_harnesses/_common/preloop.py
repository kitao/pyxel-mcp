"""Pre-loop checkpoint shared by the script-loading read_* tools."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pyxel_mcp.observe._harnesses._common.error_capture import (
    ErrorPhase,
    make_error,
    make_validation_error,
)
from pyxel_mcp.observe._harnesses._common.pyxel_patcher import (
    ObservationFinished,
    PreLoopState,
    QuitRequested,
    RunNotCalledError,
    headless_pyxel,
)
from pyxel_mcp.observe._harnesses._common.script_loader import (
    load_script_module,
    resolve_script_path,
)


class PreloopFailed(Exception):
    """A script validation, loading, or cleanup failure with a tool result."""

    def __init__(self, result: dict):
        self.result = result


def run_to_preloop(
    payload: dict[str, Any],
    *,
    empty_factory: Callable[[dict], dict],
    observe: Callable[[PreLoopState], dict[str, Any]],
) -> dict[str, Any]:
    """Run an observer synchronously when the script calls `pyxel.run`.

    Reading and artifact creation finish before unwinding the script's stack,
    so resources owned by enclosing `with`/`finally` blocks remain available.
    The patcher's sentinel then stops normal statements after `pyxel.run`.

    Script validation, import, and cleanup failures raise `PreloopFailed` with
    an empty-shaped tool result. Observer failures produce artifact errors.
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

    result: dict[str, Any] | None = None

    def on_run(state: PreLoopState) -> None:
        nonlocal result
        try:
            result = observe(state)
        except Exception as error:
            # Return to the patcher so its BaseException sentinel stops the
            # script even if the caller catches ordinary Exception around run.
            result = empty_factory(
                make_error(
                    ErrorPhase.ARTIFACT,
                    f"observation failed: {error}",
                    path=payload.get("render_path") or payload.get("output_path"),
                    capture_traceback=True,
                )
            )

    with headless_pyxel(on_run=on_run) as state:
        try:
            load_script_module(path)
            state.require_run_called()
        except ObservationFinished:
            pass
        except QuitRequested:
            if result is None:
                raise PreloopFailed(
                    empty_factory(
                        make_error(
                            ErrorPhase.SCRIPT_IMPORT,
                            "script quit before the pyxel.run checkpoint",
                            path=str(path),
                        )
                    )
                ) from None
        except RunNotCalledError as e:
            raise PreloopFailed(
                empty_factory(make_error(ErrorPhase.SCRIPT_IMPORT, str(e)))
            ) from e
        except Exception as e:
            phase = (
                ErrorPhase.SCRIPT_EXIT
                if result is not None
                else ErrorPhase.SCRIPT_IMPORT
            )
            message = f"script cleanup failed: {e}" if result is not None else str(e)
            raise PreloopFailed(
                empty_factory(
                    make_error(phase, message, path=str(path), capture_traceback=True)
                )
            ) from e

    if result is None:
        raise PreloopFailed(
            empty_factory(
                make_error(
                    ErrorPhase.SCRIPT_IMPORT, "pre-loop observation did not complete"
                )
            )
        )
    return result
