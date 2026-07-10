"""ToolError construction (spec §5.4)."""
from __future__ import annotations
import enum
import sys
import traceback
from typing import Any


class ErrorPhase(str, enum.Enum):
    VALIDATION = "validation"
    SCRIPT_IMPORT = "script_import"
    ASSET_LOAD = "asset_load"
    GAME_LOOP = "game_loop"
    UNTIL = "until"


ToolError = dict[str, Any]


def make_error(
    phase: ErrorPhase,
    message: str,
    *,
    path: str | None = None,
    frame: int | None = None,
    capture_traceback: bool = False,
) -> ToolError:
    """Build a ToolError dict.

    `path` is populated for asset_load (failing asset path) and script_import
    (script path). `frame` is populated for game_loop and until phases.
    `traceback` is populated only when capture_traceback=True AND an exception
    is currently active; otherwise None.
    """
    if not isinstance(phase, ErrorPhase):
        raise TypeError(f"phase must be ErrorPhase, got {type(phase).__name__}")
    if capture_traceback and sys.exc_info()[0] is not None:
        tb = traceback.format_exc()
    else:
        tb = None
    return {
        "phase": phase.value,
        "message": message,
        "path": path,
        "frame": frame,
        "traceback": tb,
    }


def make_validation_error(message: str, *, path: str | None = None) -> ToolError:
    """Build a validation-phase ToolError. traceback is always None for validation."""
    return make_error(ErrorPhase.VALIDATION, message, path=path)
