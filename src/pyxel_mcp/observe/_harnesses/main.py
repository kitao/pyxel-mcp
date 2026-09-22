"""Subprocess entry point.

Usage: python -m pyxel_mcp.observe._harnesses.main <subcommand>
       reads JSON parameters from stdin, writes JSON result to stdout.
       --result-file <path> keeps the result separate from script diagnostics.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Callable
from pathlib import Path

from pyxel_mcp.observe._harnesses._common.error_capture import (
    ErrorPhase,
    make_error,
    make_validation_error,
)


def _build_tools() -> dict[str, Callable[[dict], dict]]:
    """Lazy-built dispatch table. Imported on first dispatch call to avoid
    paying the pyxel-import cost at module-load time (e.g., for argv-only
    error paths that never need a tool handler).
    """
    from pyxel_mcp.observe._harnesses.tools import (
        diff_frames,
        pyxel_info,
        read_audio,
        read_image,
        read_palette,
        read_tilemap,
        run,
        validate,
    )

    return {
        "run": run.run,
        "validate": validate.run,
        "pyxel_info": pyxel_info.run,
        "read_palette": read_palette.run,
        "read_image": read_image.run,
        "read_tilemap": read_tilemap.run,
        "read_audio": read_audio.run,
        "diff_frames": diff_frames.run,
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    result_path = None
    if len(argv) == 3 and argv[1] == "--result-file":
        result_path = Path(argv[2]).resolve()
        argv = argv[:1]

    def emit(result: dict) -> None:
        text = json.dumps(result)
        if result_path is None:
            print(text)
        else:
            result_path.write_text(text, encoding="utf-8")

    if len(argv) != 1:
        msg = f"expected exactly one subcommand argument, got {len(argv)}: {argv}"
        result = {"errors": [make_validation_error(msg)]}
        emit(result)
        return 0

    subcommand = argv[0]
    raw_stdin = sys.stdin.read()

    try:
        payload = json.loads(raw_stdin) if raw_stdin.strip() else {}
    except json.JSONDecodeError as e:
        result = {"errors": [make_validation_error(f"invalid JSON on stdin: {e}")]}
        emit(result)
        return 0

    tools = _build_tools()

    if subcommand not in tools:
        result = {
            "errors": [make_validation_error(f"unknown subcommand: {subcommand}")]
        }
        emit(result)
        return 0

    handler = tools[subcommand]
    try:
        result = handler(payload)
    except Exception as e:
        # Handler-specific validation and script-load paths should catch expected
        # user errors before this process-level fallback.
        error = make_error(ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=True)
        if subcommand == "run":
            from pyxel_mcp.observe._harnesses.tools.run import _empty_result

            result = _empty_result(exit_status="crashed", errors=[error])
        else:
            result = {"errors": [error]}

    emit(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
