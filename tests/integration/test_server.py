"""End-to-end tests: invoke server.py's tool handlers directly (no MCP client)."""
import pytest
from pyxel_mcp.server import (
    run_tool, validate_tool, pyxel_info_tool,
    inspect_palette_tool, inspect_image_tool, inspect_animation_tool, inspect_tilemap_tool,
    render_audio_tool, compare_frames_tool,
    mcp,
)
from tests.conftest import SCRIPTS


def test_validate_tool_via_server():
    result = validate_tool(script=str(SCRIPTS / "minimal.py"))
    assert result["ok"] is True


def test_run_tool_via_server():
    result = run_tool(script=str(SCRIPTS / "minimal.py"), frames=3)
    assert result["exit_status"] == "ok"


def test_subprocess_timeout_enforced():
    result = run_tool(script=str(SCRIPTS / "stalling.py"), frames=1000, timeout=2)
    assert result["exit_status"] == "timeout"


async def test_run_snapshots_schema_resource_served():
    resources = await mcp.list_resources()
    uris = [str(r.uri) for r in resources]
    assert "pyxel://run-snapshots-schema" in uris
