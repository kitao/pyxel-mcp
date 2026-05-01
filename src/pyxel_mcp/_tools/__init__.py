"""MCP tool registration aggregator."""

from pyxel_mcp._tools import audio, info, inspect, run, visual


def register_tools(mcp):
    """Register all MCP tools on the given FastMCP instance."""
    run.register(mcp)
    inspect.register(mcp)
    visual.register(mcp)
    audio.register(mcp)
    info.register(mcp)
