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


@pytest.mark.asyncio
async def test_doc_resources_listed(mcp):
    resources = await mcp.list_resources()
    uris = [str(r.uri) for r in resources]
    assert "pyxel://api-reference" in uris
    assert "pyxel://user-guide" in uris
    assert "pyxel://mml-commands" in uris
    assert "pyxel://pyxres-format" in uris


@pytest.mark.asyncio
async def test_doc_cache_serves_stale_on_fetch_failure(monkeypatch, mcp):
    """When fetch fails, return the last cached value if present."""
    from pyxel_mcp._resources import docs

    url = (
        "https://raw.githubusercontent.com/kitao/pyxel/main/docs/api-reference.md"
    )
    docs._CACHE[url] = (0, "STALE")  # already expired

    def boom(_url):
        raise RuntimeError("network down")

    monkeypatch.setattr(docs, "_fetch", boom)

    contents = await mcp.read_resource("pyxel://api-reference")
    text = "".join(c.content for c in contents)
    assert text == "STALE"


@pytest.mark.asyncio
async def test_doc_cache_refetches_on_expiry(monkeypatch, mcp):
    from pyxel_mcp._resources import docs

    url = (
        "https://raw.githubusercontent.com/kitao/pyxel/main/docs/api-reference.md"
    )
    docs._CACHE[url] = (0, "OLD")  # expired

    fetched = []

    def fake_fetch(u):
        fetched.append(u)
        return "FRESH"

    monkeypatch.setattr(docs, "_fetch", fake_fetch)

    contents = await mcp.read_resource("pyxel://api-reference")
    text = "".join(c.content for c in contents)
    assert text == "FRESH"
    assert fetched == [url]


@pytest.mark.asyncio
async def test_doc_cache_uses_cache_when_fresh(monkeypatch, mcp):
    from pyxel_mcp._resources import docs

    url = (
        "https://raw.githubusercontent.com/kitao/pyxel/main/docs/api-reference.md"
    )
    # Cache is fresh (expires far in the future)
    docs._CACHE[url] = (9_999_999_999, "CACHED")

    fetched = []

    def fake_fetch(u):
        fetched.append(u)
        return "SHOULD_NOT_BE_CALLED"

    monkeypatch.setattr(docs, "_fetch", fake_fetch)

    contents = await mcp.read_resource("pyxel://api-reference")
    text = "".join(c.content for c in contents)
    assert text == "CACHED"
    assert fetched == []
