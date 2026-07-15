"""Integration smoke: drive mini_route.py through the core tool surface."""
from tests.conftest import SCRIPTS
from pyxel_mcp.server import (
    run as run_tool, validate as validate_tool,
    read_palette as read_palette_tool, read_image as read_image_tool,
)


ROUTE = str(SCRIPTS / "mini_route.py")


def test_validate_route_clean():
    result = validate_tool(script=ROUTE)
    assert result["ok"] is True


def test_run_route_with_input_and_state():
    result = run_tool(
        script=ROUTE, frames=60,
        inputs=[{"frame": 0, "buttons": ["KEY_RIGHT"]}],
        snapshots=[
            {"frame": 30, "kind": "state", "attrs": ["player_x"]},
            {"frame": 59, "kind": "state", "attrs": ["player_x", "scene"]},
        ],
    )
    assert result["exit_status"] == "ok"
    assert result["snapshots"][0]["values"]["player_x"] > 16


def test_route_log_remains_available_for_script_output():
    result = run_tool(
        script=ROUTE, frames=60,
        inputs=[{"frame": 5, "buttons": ["KEY_SPACE"]}, {"frame": 7, "buttons": []}],
    )
    assert isinstance(result["log"], str)
    assert "assertions" not in result


def test_route_palette_is_observable():
    result = read_palette_tool(script=ROUTE)
    assert result["palette_size"] == 16
    assert isinstance(result["used_indices"], list)
    assert result["errors"] == []
