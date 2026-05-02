"""ToolError construction (spec §5.4)."""
from __future__ import annotations
import enum
import traceback
from typing import Any


class ErrorPhase(str, enum.Enum):
    VALIDATION = "validation"
    SCRIPT_IMPORT = "script_import"
    ASSET_LOAD = "asset_load"
    BUILD_ASSETS = "build_assets"
    GAME_LOOP = "game_loop"
    SNAPSHOT = "snapshot"


ToolError = dict[str, Any]


def make_error(
    phase: ErrorPhase,
    message: str,
    *,
    path: str | None = None,
    frame: int | None = None,
    capture_traceback: bool = False,
) -> ToolError:
    if not isinstance(phase, ErrorPhase):
        raise TypeError(f"phase must be ErrorPhase, got {type(phase).__name__}")
    return {
        "phase": phase.value,
        "message": message,
        "path": path,
        "frame": frame,
        "traceback": traceback.format_exc() if capture_traceback else None,
    }


def make_validation_error(message: str, *, path: str | None = None) -> ToolError:
    return make_error(ErrorPhase.VALIDATION, message, path=path)
