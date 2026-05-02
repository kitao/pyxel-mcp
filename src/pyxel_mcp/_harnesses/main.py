"""Subprocess entry point (spec §11.2).

Usage: python -m pyxel_mcp._harnesses.main <subcommand>
       reads JSON parameters from stdin, writes JSON result to stdout.
"""
from __future__ import annotations
import json
import sys
from typing import Callable

from pyxel_mcp._harnesses._common.error_capture import (
    ErrorPhase, make_error, make_validation_error,
)


_TOOLS: dict[str, Callable[[dict], dict]] = {}


def register(subcommand: str):
    """Decorator: registers a tool handler under the given subcommand name."""
    def _wrap(fn: Callable[[dict], dict]) -> Callable[[dict], dict]:
        if subcommand in _TOOLS:
            raise RuntimeError(f"duplicate registration: {subcommand}")
        _TOOLS[subcommand] = fn
        return fn
    return _wrap


def _import_tool_modules() -> None:
    """Import all tool modules so their @register decorators run."""
    from pyxel_mcp._harnesses.tools import validate as _v, pyxel_info as _i, run as _r
    register("validate")(_v.run)
    register("pyxel_info")(_i.run)
    register("run")(_r.run)


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

    _import_tool_modules()

    if subcommand not in _TOOLS:
        result = {"errors": [make_validation_error(f"unknown subcommand: {subcommand}")]}
        print(json.dumps(result))
        return 0

    handler = _TOOLS[subcommand]
    try:
        result = handler(payload)
    except Exception as e:
        # TODO(phase 2): SCRIPT_IMPORT is misleading for handler-internal bugs
        # (vs actual user-script import failures). Reassess once tools start
        # using `script_loader.load_script_module` so the script-import catch
        # can be scoped tightly inside the handler. (See review on commit ef9c730.)
        result = {"errors": [make_error(ErrorPhase.SCRIPT_IMPORT, str(e), capture_traceback=True)]}

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
