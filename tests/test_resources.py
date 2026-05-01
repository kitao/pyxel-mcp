"""Tests for MCP resource registration and reading."""

import pytest

from mcp.server.fastmcp import FastMCP

from pyxel_mcp._resources import register_resources


@pytest.fixture
def mcp():
    instance = FastMCP("test")
    register_resources(instance)
    return instance


@pytest.mark.asyncio
async def test_palette_resource_listed(mcp):
    resources = await mcp.list_resources()
    uris = [str(r.uri) for r in resources]
    assert "pyxel://palette/default" in uris


@pytest.mark.asyncio
async def test_palette_resource_content(mcp):
    contents = await mcp.read_resource("pyxel://palette/default")
    # FastMCP returns an iterable of resource contents; each has a `.content` attribute
    text = "".join(c.content for c in contents)
    assert "Pyxel Default Palette" in text
    assert "black" in text  # color name 0
    assert "navy" in text   # color name 1
