"""Tests for stall_window_frames detection in run() — spec §6.5 stalled exit.

Determinism note: every run that exercises stall logic uses random_seed=42.
"""
from __future__ import annotations

import pytest

from pyxel_mcp.observe._harnesses.tools.run import run as run_tool
from tests.conftest import SCRIPTS


def test_stall_detected_via_state_buffer():
    """A script that freezes its state past frame 30, observed at every frame
    via state snapshots, must trigger exit_status='stalled'."""
    # Window 10: once we have 10 consecutive identical state.values dicts,
    # mark stalled. Schedule one state snapshot per frame for frames 10..49.
    result = run_tool({
        "script": str(SCRIPTS / "freezing_after_30.py"),
        "frames": 60,
        "random_seed": 42,
        "stall_window_frames": 10,
        "snapshots": [
            # Read only the public attr `frozen_value`; the underscore-prefixed
            # internal tick keeps advancing but is invisible to state snapshots.
            {"frames": "10:50", "kind": "state", "attrs": ["frozen_value"]},
        ],
    })
    assert result["exit_status"] == "stalled", (
        f"expected stalled, got {result['exit_status']}; "
        f"frame_count={result['frame_count']}"
    )
    # Loop should break partway — not all 60 frames executed.
    assert result["frame_count"] < 60


def test_stall_detected_via_grid_buffer():
    """When only screen_grid snapshots are available, the rolling grid hash
    buffer drives the detection."""
    result = run_tool({
        "script": str(SCRIPTS / "freezing_after_30.py"),
        "frames": 60,
        "random_seed": 42,
        "stall_window_frames": 8,
        "snapshots": [
            {"frames": "30:50", "kind": "screen_grid", "bbox": [0, 0, 64, 64]},
        ],
    })
    # frozen_value stops changing at frame 30, so screen_grid (which depends
    # on frozen_value) freezes too.
    assert result["exit_status"] == "stalled"
    assert result["frame_count"] < 60


def test_stall_inactive_without_signal_logs_warning():
    """stall_window_frames set but no state/screen_grid snapshots scheduled —
    detection has no signal, so it stays disabled and a warning is logged."""
    result = run_tool({
        "script": str(SCRIPTS / "freezing_after_30.py"),
        "frames": 40,
        "random_seed": 42,
        "stall_window_frames": 10,
        "snapshots": [],
    })
    # Without a signal, no stall is detected; the run completes normally.
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 40
    assert "stall_window_frames" in result["log"]
    assert "no signal" in result["log"] or "no `state`" in result["log"]


def test_stall_window_disabled_completes_normally():
    """With stall_window_frames=None (default), even a frozen script runs to
    completion — detection is opt-in."""
    result = run_tool({
        "script": str(SCRIPTS / "freezing_after_30.py"),
        "frames": 40,
        "random_seed": 42,
        "snapshots": [
            {"frames": "10:40", "kind": "state", "attrs": ["frozen_value"]},
        ],
    })
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 40


def test_invalid_stall_window_is_validation_error():
    """Negative or zero stall_window_frames is a validation error."""
    result = run_tool({
        "script": str(SCRIPTS / "minimal.py"),
        "frames": 5,
        "random_seed": 42,
        "stall_window_frames": 0,
    })
    assert result["exit_status"] == "invalid"
    assert result["errors"][0]["phase"] == "validation"


def test_non_freezing_script_with_stall_window_does_not_trigger():
    """A normal script that updates state every frame must not trigger
    stalled even when stall_window_frames is small."""
    result = run_tool({
        "script": str(SCRIPTS / "stateful_app.py"),
        "frames": 30,
        "random_seed": 42,
        "stall_window_frames": 5,
        "snapshots": [
            {"frames": "5:30", "kind": "state", "attrs": ["counter"]},
        ],
    })
    assert result["exit_status"] == "ok"
    assert result["frame_count"] == 30
