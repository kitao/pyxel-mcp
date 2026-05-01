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


@pytest.mark.asyncio
async def test_examples_listed_from_installed_pyxel(mcp):
    """At least the canonical 01_hello_pyxel example is enumerated."""
    resources = await mcp.list_resources()
    uris = [str(r.uri) for r in resources]
    assert "pyxel://examples/01_hello_pyxel" in uris


@pytest.mark.asyncio
async def test_example_content_returns_python(mcp):
    contents = await mcp.read_resource(
        "pyxel://examples/01_hello_pyxel"
    )
    text = "".join(c.content for c in contents)
    assert "import pyxel" in text


@pytest.mark.asyncio
async def test_examples_count_at_least_15(mcp):
    """Sanity check: enumeration finds the expected example set."""
    resources = await mcp.list_resources()
    example_uris = [str(r.uri) for r in resources if str(r.uri).startswith("pyxel://examples/")]
    assert len(example_uris) >= 15  # 20 currently, allow for future additions/removals
