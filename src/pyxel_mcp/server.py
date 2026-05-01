"""MCP server for Pyxel, a retro game engine for Python."""

import os

from mcp.server.fastmcp import FastMCP

from pyxel_mcp._resources import register_resources
from pyxel_mcp._tools import register_tools

_INSTRUCTIONS_PATH = os.path.join(os.path.dirname(__file__), "instructions.md")
try:
    with open(_INSTRUCTIONS_PATH) as f:
        _INSTRUCTIONS = f.read()
except FileNotFoundError:
    raise RuntimeError(
        f"instructions.md not found at {_INSTRUCTIONS_PATH}. "
        "Package may be corrupted — reinstall pyxel-mcp."
    )

mcp = FastMCP("pyxel-mcp", instructions=_INSTRUCTIONS)
register_tools(mcp)
register_resources(mcp)


def main():
    mcp.run()


if __name__ == "__main__":
    main()
