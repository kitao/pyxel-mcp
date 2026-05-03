import pytest
from pyxel_mcp.observe._harnesses._common.input_scheduler import (
    InputScheduler, InputEvent, ValidationError
)


def test_validates_and_sorts_events():
    events = [{"frame": 5, "buttons": ["KEY_LEFT"]}, {"frame": 0, "buttons": ["KEY_SPACE"]}]
    sched = InputScheduler(events)
    assert sched.events[0]["frame"] == 0
    assert sched.events[1]["frame"] == 5


def test_rejects_duplicate_frame():
    events = [{"frame": 5, "buttons": ["KEY_LEFT"]}, {"frame": 5, "buttons": []}]
    with pytest.raises(ValidationError, match="duplicate"):
        InputScheduler(events)


def test_rejects_unknown_button_name():
    events = [{"frame": 0, "buttons": ["KEY_NONEXISTENT"]}]
    with pytest.raises(ValidationError, match="unknown button"):
        InputScheduler(events)


def test_button_state_held_across_frames():
    """buttons set at frame 5 stays held through frame 9 (no event at 6-9)."""
    sched = InputScheduler([
        {"frame": 5, "buttons": ["KEY_LEFT"]},
        {"frame": 10, "buttons": []},
    ])
    sched.advance_to_frame(7)
    assert sched.held_buttons() == {"KEY_LEFT"}
    sched.advance_to_frame(10)
    assert sched.held_buttons() == set()


def test_buttons_field_omitted_preserves_held():
    """Event with no `buttons` field doesn't change button state."""
    sched = InputScheduler([
        {"frame": 5, "buttons": ["KEY_LEFT"]},
        {"frame": 8, "axes": {"GAMEPAD1_AXIS_LEFTX": 1.0}},
    ])
    sched.advance_to_frame(8)
    assert sched.held_buttons() == {"KEY_LEFT"}
    assert sched.held_axes() == {"GAMEPAD1_AXIS_LEFTX": 1.0}


def test_buttons_explicit_empty_releases():
    sched = InputScheduler([
        {"frame": 5, "buttons": ["KEY_LEFT", "KEY_RIGHT"]},
        {"frame": 8, "buttons": []},
    ])
    sched.advance_to_frame(8)
    assert sched.held_buttons() == set()


def test_axes_normalization_range():
    """Axes must be in [-1.0, 1.0]; out of range -> validation error."""
    with pytest.raises(ValidationError, match="axes value"):
        InputScheduler([{"frame": 0, "axes": {"GAMEPAD1_AXIS_LEFTX": 2.0}}])


def test_axes_explicit_empty_resets():
    """Symmetric to test_buttons_explicit_empty_releases: axes: {} clears all."""
    sched = InputScheduler([
        {"frame": 5, "axes": {"GAMEPAD1_AXIS_LEFTX": 1.0}},
        {"frame": 8, "axes": {}},
    ])
    sched.advance_to_frame(8)
    assert sched.held_axes() == {}


def test_rejects_unknown_axis_name():
    """Symmetric to test_rejects_unknown_button_name."""
    events = [{"frame": 0, "axes": {"GAMEPAD1_AXIS_NONEXISTENT": 0.5}}]
    with pytest.raises(ValidationError, match="unknown axis"):
        InputScheduler(events)
