"""MCP resource registration aggregator."""

from pyxel_mcp._resources import examples, palette


def register_resources(mcp):
    """Register all MCP resources on the given FastMCP instance."""
    palette.register(mcp)
    examples.register(mcp)
