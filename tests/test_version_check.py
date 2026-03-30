"""Tests for version check logic."""

import asyncio
import json
from unittest.mock import patch, MagicMock

import pytest

from pyxel_mcp.server import _check_updates


def _mock_urlopen(responses):
    """Create a mock urlopen that returns predefined responses by URL."""
    def urlopen(url, *, timeout=3):
        for pattern, data in responses.items():
            if pattern in url:
                resp = MagicMock()
                resp.read.return_value = json.dumps(data).encode()
                resp.__enter__ = lambda s: s
                resp.__exit__ = MagicMock(return_value=False)
                return resp
        raise Exception("unexpected URL")
    return urlopen


def test_update_available():
    responses = {
        "pyxel-mcp": {"info": {"version": "2.0.0"}},
        "pyxel/json": {"info": {"version": "3.0.0"}},
    }
    with patch("pyxel_mcp.server.urlopen", _mock_urlopen(responses)), \
         patch("pyxel_mcp.server._installed_version", return_value="1.0.0"):
        lines = _check_updates()
    assert len(lines) == 2
    assert "pyxel-mcp 1.0.0" in lines[0]
    assert "2.0.0" in lines[0]
    assert "pyxel 1.0.0" in lines[1]
    assert "3.0.0" in lines[1]


def test_up_to_date():
    responses = {
        "pyxel-mcp": {"info": {"version": "1.0.0"}},
        "pyxel/json": {"info": {"version": "1.0.0"}},
    }
    with patch("pyxel_mcp.server.urlopen", _mock_urlopen(responses)), \
         patch("pyxel_mcp.server._installed_version", return_value="1.0.0"):
        lines = _check_updates()
    assert lines == []


def test_network_failure_returns_empty():
    with patch("pyxel_mcp.server.urlopen", side_effect=Exception("offline")):
        lines = _check_updates()
    assert lines == []


def test_partial_failure():
    """One package check fails, the other succeeds."""
    call_count = 0
    def flaky_urlopen(url, *, timeout=3):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("timeout")
        resp = MagicMock()
        resp.read.return_value = json.dumps({"info": {"version": "9.0.0"}}).encode()
        resp.__enter__ = lambda s: s
        resp.__exit__ = MagicMock(return_value=False)
        return resp

    with patch("pyxel_mcp.server.urlopen", flaky_urlopen), \
         patch("pyxel_mcp.server._installed_version", return_value="1.0.0"):
        lines = _check_updates()
    # First package (pyxel-mcp) fails, second (pyxel) succeeds
    assert len(lines) == 1
    assert "pyxel " in lines[0]


@pytest.mark.asyncio
async def test_pyxel_info_includes_update_notice():
    responses = {
        "pyxel-mcp": {"info": {"version": "99.0.0"}},
        "pyxel/json": {"info": {"version": "99.0.0"}},
    }
    with patch("pyxel_mcp.server.urlopen", _mock_urlopen(responses)), \
         patch("pyxel_mcp.server._installed_version", return_value="1.0.0"), \
         patch("pyxel_mcp.server._pyxel_dir", return_value="/fake/pyxel"):
        from pyxel_mcp.server import pyxel_info
        result = await pyxel_info()
    assert "Update available: pyxel-mcp" in result
    assert "Update available: pyxel" in result


@pytest.mark.asyncio
async def test_pyxel_info_no_notice_when_current():
    responses = {
        "pyxel-mcp": {"info": {"version": "1.0.0"}},
        "pyxel/json": {"info": {"version": "1.0.0"}},
    }
    with patch("pyxel_mcp.server.urlopen", _mock_urlopen(responses)), \
         patch("pyxel_mcp.server._installed_version", return_value="1.0.0"), \
         patch("pyxel_mcp.server._pyxel_dir", return_value="/fake/pyxel"):
        from pyxel_mcp.server import pyxel_info
        result = await pyxel_info()
    assert "Update available" not in result
