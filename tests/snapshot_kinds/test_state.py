"""Tests for snapshot_kinds.state (spec §6.4.3)."""
from pyxel_mcp._harnesses._common.snapshot_kinds.state import capture


class _AppMock:
    """Stand-in for an App instance for unit tests (no Pyxel required)."""
    def __init__(self):
        self.counter = 5
        self.lives = 3
        self.message = "hello"
        self.player = type("P", (), {"x": 10, "y": 20})()
        self.barrels = [type("B", (), {"x": 50, "y": 100})(),
                        type("B", (), {"x": 60, "y": 110})()]
        self.scores = [100, 200, 300]


def test_attrs_none_returns_top_level_scalars():
    app = _AppMock()
    result = capture({"frame": 0, "kind": "state"}, app_instance=app, module=None)
    assert "counter" in result["values"]
    assert "lives" in result["values"]
    assert "message" in result["values"]
    # Composite types skipped
    assert "player" not in result["values"]
    assert "barrels" not in result["values"]


def test_attrs_empty_list_returns_empty():
    app = _AppMock()
    result = capture({"frame": 0, "kind": "state", "attrs": []}, app_instance=app, module=None)
    assert result["values"] == {}


def test_dotted_path():
    app = _AppMock()
    result = capture(
        {"frame": 0, "kind": "state", "attrs": ["player.x", "player.y"]},
        app_instance=app, module=None,
    )
    assert result["values"]["player.x"] == 10
    assert result["values"]["player.y"] == 20


def test_indexed_path():
    app = _AppMock()
    result = capture(
        {"frame": 0, "kind": "state", "attrs": ["barrels[0].y", "barrels[1].x"]},
        app_instance=app, module=None,
    )
    assert result["values"]["barrels[0].y"] == 100
    assert result["values"]["barrels[1].x"] == 60


def test_missing_attr_warning():
    app = _AppMock()
    result = capture(
        {"frame": 0, "kind": "state", "attrs": ["nonexistent"]},
        app_instance=app, module=None,
    )
    assert "nonexistent" not in result["values"]
    assert any("nonexistent" in w for w in result["warnings"])


def test_bare_function_warns_and_uses_module():
    import types
    mod = types.ModuleType("fake")
    mod.counter = 7
    result = capture({"frame": 0, "kind": "state"}, app_instance=None, module=mod)
    assert result["values"]["counter"] == 7
    assert any("no app class" in w.lower() for w in result["warnings"])
