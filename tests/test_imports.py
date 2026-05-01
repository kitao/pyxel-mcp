"""Verify all package modules import cleanly."""

import importlib

PACKAGES = [
    "pyxel_mcp",
    "pyxel_mcp.server",
    "pyxel_mcp._common",
    "pyxel_mcp._common.audio",
    "pyxel_mcp._common.errors",
    "pyxel_mcp._common.format",
    "pyxel_mcp._common.headless",
    "pyxel_mcp._common.palette",
    "pyxel_mcp._common.pyxel_env",
    "pyxel_mcp._common.subprocess",
    "pyxel_mcp._common.validate",
    "pyxel_mcp._tools",
    "pyxel_mcp._tools.run",
    "pyxel_mcp._tools.inspect",
    "pyxel_mcp._tools.visual",
    "pyxel_mcp._tools.audio",
    "pyxel_mcp._tools.info",
    "pyxel_mcp._resources",
    "pyxel_mcp._harnesses",
]


def test_all_modules_import():
    for name in PACKAGES:
        importlib.import_module(name)


def test_main_callable():
    from pyxel_mcp.server import main
    assert callable(main)
