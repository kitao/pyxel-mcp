"""Tests for _headless module helpers."""

import os
import sys
import types
from unittest.mock import MagicMock, call, patch


def _make_mock_pyxel():
    """Create a minimal mock pyxel module."""
    mock = MagicMock()
    mock.run = MagicMock()
    mock.show = MagicMock()
    mock.flip = MagicMock()
    mock.frame_count = 0
    return mock


# --- setup_harness ---

def test_setup_harness_resets_argv(tmp_path):
    """setup_harness resets sys.argv to [script_path]."""
    script = str(tmp_path / "game.py")
    original_argv = sys.argv[:]

    mock_pyxel = _make_mock_pyxel()
    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from pyxel_mcp._headless import setup_harness
        sys.argv = ["harness.py", script, "out.png", "30"]
        setup_harness(script)
        assert sys.argv == [script]

    sys.argv = original_argv


def test_setup_harness_calls_patch_headless_init(tmp_path):
    """setup_harness calls patch_headless_init with script_path."""
    script = str(tmp_path / "game.py")

    mock_pyxel = _make_mock_pyxel()
    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        import pyxel_mcp._headless as headless
        with patch.object(headless, "patch_headless_init") as mock_patch:
            headless.setup_harness(script)
            mock_patch.assert_called_once_with(script, None)


def test_setup_harness_passes_transform_args(tmp_path):
    """setup_harness forwards transform_args to patch_headless_init."""
    script = str(tmp_path / "game.py")
    transform = lambda args: args

    mock_pyxel = _make_mock_pyxel()
    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        import pyxel_mcp._headless as headless
        with patch.object(headless, "patch_headless_init") as mock_patch:
            headless.setup_harness(script, transform)
            mock_patch.assert_called_once_with(script, transform)


# --- patch_game_loop ---

def test_patch_game_loop_patches_run_show_flip():
    """patch_game_loop replaces pyxel.run, pyxel.show, pyxel.flip."""
    mock_pyxel = _make_mock_pyxel()
    original_run = mock_pyxel.run
    original_show = mock_pyxel.show
    original_flip = mock_pyxel.flip

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.patch_game_loop(lambda frame, draw: False)

    assert mock_pyxel.run is not original_run
    assert mock_pyxel.show is not original_show
    assert mock_pyxel.flip is not original_flip


def test_patch_game_loop_on_frame_receives_frame_count():
    """patch_game_loop calls on_frame with pyxel.frame_count and draw fn."""
    received = []

    def on_frame(frame_count, draw):
        received.append(frame_count)
        return True  # exit after first frame

    mock_pyxel = _make_mock_pyxel()
    mock_pyxel.frame_count = 42

    # Simulate pyxel.run calling wrapped_update once then os._exit
    captured_run = {}

    def fake_original_run(update, draw):
        captured_run["update"] = update
        captured_run["draw"] = draw

    mock_pyxel.run = fake_original_run

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.patch_game_loop(on_frame)

    # Call the patched run
    draw_fn = MagicMock()
    update_fn = MagicMock()
    mock_pyxel.run(update_fn, draw_fn)

    # Simulate the wrapped update calling on_frame — should get frame_count=42
    with patch("os._exit"):
        captured_run["update"]()

    assert received == [42]


def test_patch_game_loop_run_exits_when_on_frame_returns_true():
    """patch_game_loop calls os._exit(0) when on_frame returns True."""
    mock_pyxel = _make_mock_pyxel()
    mock_pyxel.frame_count = 1

    captured_update = {}

    def fake_original_run(update, draw):
        captured_update["fn"] = update

    mock_pyxel.run = fake_original_run

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.patch_game_loop(lambda frame, draw: True)

    mock_pyxel.run(MagicMock(), MagicMock())

    with patch("os._exit") as mock_exit:
        captured_update["fn"]()
        mock_exit.assert_called_once_with(0)


def test_patch_game_loop_show_calls_on_show():
    """patch_game_loop calls on_show when pyxel.show() is invoked."""
    on_show_called = []

    def on_show():
        on_show_called.append(True)

    mock_pyxel = _make_mock_pyxel()

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.patch_game_loop(lambda frame, draw: False, on_show=on_show)

    with patch("os._exit"):
        mock_pyxel.show()

    assert on_show_called == [True]


def test_patch_game_loop_show_default_calls_on_frame():
    """patch_game_loop calls on_frame(0, ...) for pyxel.show() when no on_show."""
    received = []

    def on_frame(frame_count, draw):
        received.append(frame_count)
        return False

    mock_pyxel = _make_mock_pyxel()

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.patch_game_loop(on_frame)

    with patch("os._exit"):
        mock_pyxel.show()

    assert received == [0]


def test_patch_game_loop_flip_increments_counter():
    """patch_game_loop tracks flip call count and passes it to on_frame."""
    received_frames = []

    def on_frame(frame_count, draw):
        received_frames.append(frame_count)
        return frame_count >= 2  # exit after 2 flips

    mock_pyxel = _make_mock_pyxel()

    # Keep track of original flip being called
    flip_calls = []
    mock_pyxel.flip = MagicMock(side_effect=lambda: flip_calls.append(True))

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.patch_game_loop(on_frame)

    with patch("os._exit"):
        mock_pyxel.flip()  # frame 1 — on_frame returns False
        mock_pyxel.flip()  # frame 2 — on_frame returns True, exits

    assert received_frames == [1, 2]


# --- noop_game_loop ---

def test_noop_game_loop_patches_run_show_flip():
    """noop_game_loop replaces run/show/flip with callables."""
    mock_pyxel = _make_mock_pyxel()

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.noop_game_loop()

    # All three should now be callable no-ops
    assert callable(mock_pyxel.run)
    assert callable(mock_pyxel.show)
    assert callable(mock_pyxel.flip)


def test_noop_game_loop_run_does_nothing():
    """noop_game_loop makes pyxel.run() a no-op (doesn't call update/draw)."""
    mock_pyxel = _make_mock_pyxel()
    update = MagicMock()
    draw = MagicMock()

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.noop_game_loop()

    mock_pyxel.run(update, draw)

    update.assert_not_called()
    draw.assert_not_called()


def test_noop_game_loop_show_does_nothing():
    """noop_game_loop makes pyxel.show() a no-op."""
    mock_pyxel = _make_mock_pyxel()

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.noop_game_loop()

    # Should not raise, should return None
    result = mock_pyxel.show()
    assert result is None


def test_noop_game_loop_flip_does_nothing():
    """noop_game_loop makes pyxel.flip() a no-op."""
    mock_pyxel = _make_mock_pyxel()

    with patch.dict(sys.modules, {"pyxel": mock_pyxel}):
        from importlib import reload
        import pyxel_mcp._headless as headless
        reload(headless)
        headless.noop_game_loop()

    # Should not raise, should return None
    result = mock_pyxel.flip()
    assert result is None
