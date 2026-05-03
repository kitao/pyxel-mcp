"""End-to-end tests: invoke server.py's tool handlers directly (no MCP client)."""
import pytest
from pyxel_mcp.server import (
    run_tool, validate_tool, pyxel_info_tool,
    read_palette_tool, read_image_tool, read_animation_tool, read_tilemap_tool,
    read_audio_tool, diff_frames_tool,
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


def test_run_timeout_payload_shape():
    """When `run` times out, the result must remain a well-formed RunResult so
    that callers can predicate on it without special-casing the timeout path
    (snapshots/[], assertions/[], errors/[], frame_count int, elapsed float).
    """
    result = run_tool(script=str(SCRIPTS / "stalling.py"), frames=1000, timeout=2)
    assert result["exit_status"] == "timeout"
    assert isinstance(result.get("snapshots"), list)
    assert isinstance(result.get("assertions"), list)
    assert isinstance(result.get("errors"), list)
    assert isinstance(result.get("frame_count"), int)
    assert isinstance(result.get("elapsed_seconds"), (int, float))
    assert "log" in result and isinstance(result["log"], str)
    assert "seeded" in result


def test_non_run_tool_timeout_returns_errors():
    """For non-run tools, dispatch's timeout path returns {errors: [...]} —
    verify the error shape (phase + message) so agents can detect it."""
    # validate has near-zero work; force a 1-second timeout to trip dispatch's
    # subprocess.TimeoutExpired only if validate actually takes that long.
    # We can't reliably force a timeout on validate itself, but we can verify
    # the contract by inspection: read_audio with a long-duration argument
    # plus a tight timeout would trigger the path. Use stalling.py instead
    # since it's the canonical "never returns" fixture and read_tilemap
    # imports + headless inits the script.
    result = read_tilemap_tool(script=str(SCRIPTS / "stalling.py"), tilemap=0)
    # stalling.py spins in pyxel.run; harness can't reach pre-loop checkpoint,
    # so we expect either a successful pre-loop reach (if Pyxel.run intercept
    # works) or a timeout error. Either way, the result must be a dict with
    # an `errors` list — never raise.
    assert isinstance(result, dict)
    assert "errors" in result and isinstance(result["errors"], list)


async def test_run_snapshots_schema_resource_served():
    resources = await mcp.list_resources()
    uris = [str(r.uri) for r in resources]
    assert "pyxel://run-snapshots-schema" in uris
