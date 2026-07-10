"""Subprocess entry point.

Usage: python -m pyxel_mcp.observe._harnesses.main <subcommand>
       reads JSON parameters from stdin, writes JSON result to stdout.
"""
from __future__ import annotations
import json
import sys
from typing import Callable

from pyxel_mcp.observe._harnesses._common.error_capture import (
    ErrorPhase, make_error, make_validation_error,
)


def _build_tools() -> dict[str, Callable[[dict], dict]]:
    """Lazy-built dispatch table. Imported on first dispatch call to avoid
    paying the pyxel-import cost at module-load time (e.g., for argv-only
    error paths that never need a tool handler).
    """
    from pyxel_mcp.observe._harnesses.tools import (
        run, validate, pyxel_info,
        read_palette, read_image, read_animation, read_tilemap,
        read_audio, diff_frames,
    )
    return {
        "run": run.run,
        "validate": validate.run,
        "pyxel_info": pyxel_info.run,
        "read_palette": read_palette.run,
        "read_image": read_image.run,
        "read_animation": read_animation.run,
        "read_tilemap": read_tilemap.run,
        "read_audio": read_audio.run,
        "diff_frames": diff_frames.run,
    }


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if len(argv) != 1:
        msg = f"expected exactly one subcommand argument, got {len(argv)}: {argv}"
        result = {"errors": [make_validation_error(msg)]}
        print(json.dumps(result))
        return 0

    subcommand = argv[0]
    raw_stdin = sys.stdin.read()

    try:
        payload = json.loads(raw_stdin) if raw_stdin.strip() else {}
    except json.JSONDecodeError as e:
        result = {"errors": [make_validation_error(f"invalid JSON on stdin: {e}")]}
        print(json.dumps(result))
        return 0

    tools = _build_tools()

    if subcommand not in tools:
        result = {"errors": [make_validation_error(f"unknown subcommand: {subcommand}")]}
        print(json.dumps(result))
        return 0

    handler = tools[subcommand]
    try:
        result = handler(payload)
    except Exception as e:
        # Handler-specific validation and script-load paths should catch expected
        # user errors before this process-level fallback.
        result = {"errors": [make_error(ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=True)]}

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
