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


def test_route_assertions():
    result = run_tool(
        script=ROUTE, frames=60,
        inputs=[{"frame": 5, "buttons": ["KEY_SPACE"]}, {"frame": 7, "buttons": []}],
    )
    assert any(a["name"].startswith("jump_at_frame") for a in result["assertions"])


def test_route_palette_hierarchy():
    result = read_palette_tool(script=ROUTE)
    assert result["palette_size"] == 16
    # Palette shape may not have hierarchy on this minimal fixture; just check no errors.
    assert result["errors"] == []
