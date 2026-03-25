"""Subprocess execution for MCP tool harnesses."""

import asyncio
import json
import os
import sys

from pyxel_mcp._errors import decode_stderr, extract_stdout

_PKG_DIR = os.path.dirname(__file__)

HARNESS_PATHS = {
    "run": os.path.join(_PKG_DIR, "harness.py"),
    "audio": os.path.join(_PKG_DIR, "audio_harness.py"),
    "sprite": os.path.join(_PKG_DIR, "sprite_harness.py"),
    "frames": os.path.join(_PKG_DIR, "frames_harness.py"),
    "layout": os.path.join(_PKG_DIR, "layout_harness.py"),
    "input": os.path.join(_PKG_DIR, "input_harness.py"),
    "state": os.path.join(_PKG_DIR, "state_harness.py"),
    "screen": os.path.join(_PKG_DIR, "screen_harness.py"),
    "tilemap": os.path.join(_PKG_DIR, "tilemap_harness.py"),
    "bank": os.path.join(_PKG_DIR, "bank_harness.py"),
}


async def run_harness(harness_name, args, *, cwd, timeout=10):
    """Run a harness subprocess and return (json_data, user_output, stderr_text).

    Raises asyncio.TimeoutError on timeout, RuntimeError on non-zero exit.
    Returns (None, user_output, stderr_text) when no JSON in stdout.
    """
    harness_path = HARNESS_PATHS[harness_name]
    proc = await asyncio.create_subprocess_exec(
        sys.executable, harness_path, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await asyncio.wait_for(
        proc.communicate(), timeout=timeout
    )

    stderr_text = decode_stderr(stderr)

    if proc.returncode != 0:
        error_msg = stderr_text or "Unknown error"
        raise RuntimeError(
            f"Harness failed (exit code {proc.returncode}): {error_msg}"
        )

    json_data = None
    user_output = ""
    if stdout:
        json_str, user_output = extract_stdout(stdout)
        if json_str:
            try:
                json_data = json.loads(json_str)
            except json.JSONDecodeError:
                # No valid JSON in stdout; treat the whole output as user text
                user_output = json_str if not user_output else user_output

    return json_data, user_output, stderr_text
