"""Subprocess execution for MCP tool harnesses."""

import asyncio
import json
import sys

from pyxel_mcp._common.errors import decode_stderr, extract_stdout

HARNESS_MODULES = {
    "run": "pyxel_mcp._harnesses.main",
    "audio": "pyxel_mcp._harnesses.audio",
    "sprite": "pyxel_mcp._harnesses.sprite",
    "frames": "pyxel_mcp._harnesses.frames",
    "layout": "pyxel_mcp._harnesses.layout",
    "input": "pyxel_mcp._harnesses.input",
    "state": "pyxel_mcp._harnesses.state",
    "screen": "pyxel_mcp._harnesses.screen",
    "tilemap": "pyxel_mcp._harnesses.tilemap",
    "bank": "pyxel_mcp._harnesses.bank",
    "record": "pyxel_mcp._harnesses.record",
}


async def run_harness_raw(harness_key, args, *, cwd, timeout=10):
    """Run a harness subprocess and return (stdout_bytes, stderr_text, returncode).

    Unlike run_harness(), does not parse JSON — returns raw stdout bytes.
    Raises asyncio.TimeoutError on timeout (process is killed first).
    """
    module = HARNESS_MODULES[harness_key]
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", module, *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout, stderr = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        raise

    return stdout, decode_stderr(stderr), proc.returncode


async def run_harness(harness_name, args, *, cwd, timeout=10):
    """Run a harness subprocess and return (json_data, user_output, stderr_text).

    Raises asyncio.TimeoutError on timeout, RuntimeError on non-zero exit.
    Returns (None, user_output, stderr_text) when no JSON in stdout.
    """
    module = HARNESS_MODULES[harness_name]
    proc = await asyncio.create_subprocess_exec(
        sys.executable, "-m", module, *args,
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
                user_output = json_str if not user_output else user_output

    return json_data, user_output, stderr_text
