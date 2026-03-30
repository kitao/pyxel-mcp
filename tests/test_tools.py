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

@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_and_capture(game_script_path):
    from pyxel_mcp.server import run_and_capture
    result = await run_and_capture(game_script_path, frames=1, scale=1, timeout=10)
    assert len(result) >= 2
    assert "Captured" in str(result[-1])

@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_script_valid(script_path):
    from pyxel_mcp.server import validate_script
    result = await validate_script(script_path)
    assert "Script:" in result

@pytest.mark.integration
@pytest.mark.asyncio
async def test_validate_script_syntax_error():
    from pyxel_mcp.server import validate_script
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write("def broken(\n")
        path = f.name
    try:
        result = await validate_script(path)
        assert "Syntax error" in result
    finally:
        os.unlink(path)

@pytest.mark.integration
@pytest.mark.asyncio
async def test_inspect_screen(script_path):
    from pyxel_mcp.server import inspect_screen
    result = await inspect_screen(script_path, frame=1, timeout=10)
    assert "32x32" in result

@pytest.mark.integration
@pytest.mark.asyncio
async def test_inspect_layout(game_script_path):
    from pyxel_mcp.server import inspect_layout
    result = await inspect_layout(game_script_path, frame=2, timeout=10)
    assert "Screen:" in result

@pytest.mark.integration
@pytest.mark.asyncio
async def test_inspect_palette(game_script_path):
    from pyxel_mcp.server import inspect_palette
    result = await inspect_palette(game_script_path, frame=2, timeout=10)
    assert "Colors used:" in result or "Palette" in result

@pytest.mark.integration
@pytest.mark.asyncio
async def test_compare_frames(game_script_path):
    from pyxel_mcp.server import compare_frames
    result = await compare_frames(game_script_path, frame_a=1, frame_b=5, timeout=10)
    assert "Frame" in result

@pytest.mark.integration
@pytest.mark.asyncio
async def test_run_and_capture_not_found():
    from pyxel_mcp.server import run_and_capture
    result = await run_and_capture("/nonexistent/script.py")
    assert "Error" in str(result[0]) or "not found" in str(result[0])
