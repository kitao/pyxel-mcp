"""Tests for snapshot_kinds.state."""

import pytest

from pyxel_mcp.observe._harnesses._common.snapshot_kinds.state import (
    capture,
    capture_static,
)


class _AppMock:
    """Stand-in for an App instance for unit tests (no Pyxel required)."""

    def __init__(self):
        self.counter = 5
        self.lives = 3
        self.message = "hello"
        self.player = type("P", (), {"x": 10, "y": 20})()
        self.hazards = [
            type("H", (), {"x": 50, "y": 100})(),
            type("H", (), {"x": 60, "y": 110})(),
        ]
        self.scores = [100, 200, 300]


def test_attrs_none_returns_top_level_scalars():
    app = _AppMock()
    result = capture({"frame": 0, "kind": "state"}, app_instance=app, module=None)
    assert "counter" in result["values"]
    assert "lives" in result["values"]
    assert "message" in result["values"]
    # Composite types skipped
    assert "player" not in result["values"]
    assert "hazards" not in result["values"]


def test_attrs_empty_list_returns_empty():
    app = _AppMock()
    result = capture(
        {"frame": 0, "kind": "state", "attrs": []}, app_instance=app, module=None
    )
    assert result["values"] == {}


def test_dotted_path():
    app = _AppMock()
    result = capture(
        {"frame": 0, "kind": "state", "attrs": ["player.x", "player.y"]},
        app_instance=app,
        module=None,
    )
    assert result["values"]["player.x"] == 10
    assert result["values"]["player.y"] == 20


def test_indexed_path():
    app = _AppMock()
    result = capture(
        {"frame": 0, "kind": "state", "attrs": ["hazards[0].y", "hazards[1].x"]},
        app_instance=app,
        module=None,
    )
    assert result["values"]["hazards[0].y"] == 100
    assert result["values"]["hazards[1].x"] == 60


def test_missing_attr_warning():
    app = _AppMock()
    result = capture(
        {"frame": 0, "kind": "state", "attrs": ["nonexistent"]},
        app_instance=app,
        module=None,
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


@pytest.mark.parametrize("nested", [False, True])
def test_static_capture_does_not_invoke_custom_metaclasses(nested):
    calls = []

    class Meta(type):
        def __getattribute__(cls, name):
            calls.append(name)
            return super().__getattribute__(name)

        def __eq__(cls, other):
            calls.append("comparison")
            return super().__eq__(other)

    class Dynamic(metaclass=Meta):
        score = 3

    if nested:
        app = _AppMock()
        app.value = Dynamic()
        attrs = ["value"]
    else:
        app = Dynamic()
        attrs = ["score"]
    calls.clear()
    result = capture_static({"frame": 0, "attrs": attrs}, app_instance=app, module=None)
    assert result["values"] == {}
    assert result["warnings"]
    assert calls == []


@pytest.mark.parametrize("attrs", [None, ["score"]])
def test_static_capture_does_not_invoke_attribute_dictionary_key_hooks(attrs):
    calls = []

    class Name(str):
        def __eq__(self, other):
            calls.append("comparison")
            return super().__eq__(other)

        __hash__ = str.__hash__

        def startswith(self, *args):
            calls.append("startswith")
            return super().startswith(*args)

    app = _AppMock()
    setattr(app, Name("score"), 3)
    calls.clear()
    result = capture_static({"frame": 0, "attrs": attrs}, app_instance=app, module=None)
    assert result["values"] == {}
    assert result["warnings"]
    assert calls == []


def test_static_capture_keeps_slots_and_numpy_float64_scalars():
    import numpy as np

    class Slotted:
        __slots__ = ("probability", "score")

    app = Slotted()
    app.score = 3
    app.probability = np.float64(0.5)
    result = capture_static({"frame": 0}, app_instance=app, module=None)
    assert result["values"] == {"score": 3, "probability": 0.5}
