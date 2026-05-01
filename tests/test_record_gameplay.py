"""Tests for record_gameplay tool."""

import pytest


@pytest.fixture
def trivial_script(tmp_path):
    """A minimal Pyxel script that draws a moving square."""
    script = tmp_path / "anim.py"
    script.write_text(
        """
import pyxel

class App:
    def __init__(self):
        pyxel.init(64, 64)
        self.x = 0
        pyxel.run(self.update, self.draw)

    def update(self):
        self.x = (self.x + 1) % 64

    def draw(self):
        pyxel.cls(0)
        pyxel.rect(self.x, 28, 8, 8, 11)

App()
"""
    )
    return str(script)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_record_gameplay_returns_gif(trivial_script):
    """record_gameplay returns a non-empty GIF for a valid script."""
    from pyxel_mcp._tools.run import _record_gameplay_impl

    img = await _record_gameplay_impl(trivial_script, duration=20, scale=1, timeout=20)
    # MCP Image: img.data is bytes containing GIF magic header
    assert hasattr(img, "data"), f"expected Image, got {type(img).__name__}: {img!r}"
    assert img.data[:6] in (b"GIF87a", b"GIF89a"), f"unexpected header: {img.data[:6]!r}"


@pytest.mark.asyncio
async def test_record_gameplay_invalid_script_path():
    from pyxel_mcp._tools.run import _record_gameplay_impl
    result = await _record_gameplay_impl("/nonexistent.py", duration=10)
    assert isinstance(result, str)
    assert "script not found" in result


@pytest.mark.asyncio
async def test_record_gameplay_invalid_json_inputs(trivial_script):
    from pyxel_mcp._tools.run import _record_gameplay_impl
    result = await _record_gameplay_impl(trivial_script, duration=10, inputs="not-json")
    assert isinstance(result, str)
    assert "not valid JSON" in result
