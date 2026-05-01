"""Tests for _subprocess module."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pyxel_mcp._common.subprocess import HARNESS_PATHS, run_harness


def test_harness_paths_keys():
    """HARNESS_PATHS must have exactly 10 entries with expected keys."""
    expected_keys = {
        "run", "audio", "sprite", "frames", "layout",
        "input", "state", "screen", "tilemap", "bank",
    }
    assert set(HARNESS_PATHS.keys()) == expected_keys
    assert len(HARNESS_PATHS) == 10


def test_harness_paths_values_are_strings():
    """All harness paths must be string values."""
    for key, path in HARNESS_PATHS.items():
        assert isinstance(path, str), f"HARNESS_PATHS[{key!r}] is not a string"


def _make_mock_proc(returncode, stdout_bytes, stderr_bytes):
    """Create a mock subprocess process with communicate() returning given bytes."""
    proc = MagicMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout_bytes, stderr_bytes))
    return proc


@pytest.mark.asyncio
async def test_run_harness_success_returns_json():
    """run_harness returns parsed JSON data on success."""
    payload = {"result": 42, "ok": True}
    stdout = json.dumps(payload).encode()
    mock_proc = _make_mock_proc(0, stdout, b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        json_data, user_output, stderr_text = await run_harness(
            "sprite", ["script.py", "0", "0", "0", "8", "8"],
            cwd="/tmp",
        )

    assert json_data == payload
    assert user_output == ""
    assert stderr_text == ""


@pytest.mark.asyncio
async def test_run_harness_raises_on_nonzero_exit():
    """run_harness raises RuntimeError when returncode != 0."""
    mock_proc = _make_mock_proc(1, b"", b"Something went wrong")

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(RuntimeError, match="Harness failed"):
            await run_harness("layout", ["script.py", "5"], cwd="/tmp")


@pytest.mark.asyncio
async def test_run_harness_no_json_returns_none():
    """run_harness returns (None, user_output, stderr) when stdout has no JSON."""
    mock_proc = _make_mock_proc(0, b"plain text output with no json", b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        json_data, user_output, stderr_text = await run_harness(
            "state", ["script.py", "60"], cwd="/tmp"
        )

    assert json_data is None
    assert "plain text" in user_output
    assert stderr_text == ""


@pytest.mark.asyncio
async def test_run_harness_timeout_propagates():
    """run_harness propagates asyncio.TimeoutError on timeout."""
    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        with pytest.raises(asyncio.TimeoutError):
            await run_harness("screen", ["script.py", "5"], cwd="/tmp", timeout=1)


@pytest.mark.asyncio
async def test_run_harness_user_output_separated():
    """run_harness separates user print output from JSON."""
    payload = {"pixels": [[0, 1], [2, 3]]}
    stdout = b"Debug: loading done\n" + json.dumps(payload).encode()
    mock_proc = _make_mock_proc(0, stdout, b"")

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        json_data, user_output, stderr_text = await run_harness(
            "tilemap", ["script.py", "0", "1"], cwd="/tmp"
        )

    assert json_data == payload
    assert "Debug: loading done" in user_output
