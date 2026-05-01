"""Integration tests for MCP tools (require Pyxel)."""

import asyncio
import os
import tempfile
import pytest

MINIMAL_SCRIPT = '''\
import pyxel
pyxel.init(32, 32)
pyxel.cls(1)
pyxel.rect(4, 4, 24, 24, 8)
pyxel.show()
'''

GAME_LOOP_SCRIPT = '''\
import pyxel

class App:
    def __init__(self):
        pyxel.init(32, 32)
        pyxel.run(self.update, self.draw)
    def update(self):
        pass
    def draw(self):
        pyxel.cls(0)
        pyxel.rect(8, 8, 16, 16, 7)

App()
'''

@pytest.fixture
def script_path():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(MINIMAL_SCRIPT)
        path = f.name
    yield path
    os.unlink(path)

@pytest.fixture
def game_script_path():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(GAME_LOOP_SCRIPT)
        path = f.name
    yield path
    os.unlink(path)

async def _call_tool(name, **kwargs):
    """Invoke a registered MCP tool by name."""
    from pyxel_mcp.server import mcp
    return await mcp.call_tool(name, kwargs)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_and_capture(game_script_path):
    result = await _call_tool(
        "run_and_capture",
        script_path=game_script_path, frames=1, scale=1, timeout=10,
    )
    assert "Captured" in str(result)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_script_valid(script_path):
    result = await _call_tool("validate_script", script_path=script_path)
    assert "Script:" in str(result)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_script_syntax_error():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def broken(\n")
        path = f.name
    try:
        result = await _call_tool("validate_script", script_path=path)
        assert "Syntax error" in str(result)
    finally:
        os.unlink(path)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_inspect_screen(script_path):
    result = await _call_tool(
        "inspect_screen", script_path=script_path, frame=1, timeout=10,
    )
    assert "32x32" in str(result)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_inspect_layout(game_script_path):
    result = await _call_tool(
        "inspect_layout", script_path=game_script_path, frame=2, timeout=10,
    )
    assert "Screen:" in str(result)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_inspect_palette(game_script_path):
    result = await _call_tool(
        "inspect_palette", script_path=game_script_path, frame=2, timeout=10,
    )
    text = str(result)
    assert "Colors used:" in text or "Palette" in text

@pytest.mark.integration
@pytest.mark.asyncio
async def test_compare_frames(game_script_path):
    result = await _call_tool(
        "compare_frames",
        script_path=game_script_path, frame_a=1, frame_b=5, timeout=10,
    )
    assert "Frame" in str(result)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_and_capture_not_found():
    result = await _call_tool(
        "run_and_capture", script_path="/nonexistent/script.py",
    )
    text = str(result)
    assert "Error" in text or "not found" in text
