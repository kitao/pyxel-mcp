import os

import pytest

from pyxel_mcp.observe._harnesses._common.pyxel_patcher import (
    ObservationFinished,
    QuitRequested,
    RunNotCalledError,
    headless_pyxel,
)


def test_sets_sdl_videodriver():
    with headless_pyxel():
        assert os.environ.get("SDL_VIDEODRIVER") == "dummy"


def test_sets_and_restores_sdl_audiodriver(monkeypatch):
    monkeypatch.setenv("SDL_AUDIODRIVER", "coreaudio")
    with headless_pyxel():
        assert os.environ.get("SDL_AUDIODRIVER") == "dummy"
    assert os.environ.get("SDL_AUDIODRIVER") == "coreaudio"


def test_removes_sdl_audiodriver_when_absent(monkeypatch):
    monkeypatch.delenv("SDL_AUDIODRIVER", raising=False)
    with headless_pyxel():
        assert os.environ.get("SDL_AUDIODRIVER") == "dummy"
    assert os.environ.get("SDL_AUDIODRIVER") is None


def test_captures_callbacks():
    import pyxel

    update_fn = lambda: None
    draw_fn = lambda: None
    with headless_pyxel() as state:
        pyxel.init(64, 64)
        pyxel.run(update_fn, draw_fn)
    assert state.update_callback is update_fn
    assert state.draw_callback is draw_fn


def test_app_instance_resolved_from_bound_method():
    import pyxel

    class App:
        def update(self):
            pass

        def draw(self):
            pass

    app = App()
    with headless_pyxel() as state:
        pyxel.init(64, 64)
        pyxel.run(app.update, app.draw)
    assert state.app_instance is app


def test_app_instance_none_for_bare_function():
    import pyxel

    update_fn = lambda: None
    draw_fn = lambda: None
    with headless_pyxel() as state:
        pyxel.init(64, 64)
        pyxel.run(update_fn, draw_fn)
    assert state.app_instance is None


def test_run_not_called_raises():
    with headless_pyxel() as state:
        pass  # script doesn't call pyxel.run
    with pytest.raises(RunNotCalledError):
        state.require_run_called()


def test_on_run_drives_callbacks_before_surrounding_resources_close():
    import contextlib

    import pyxel

    events = []

    @contextlib.contextmanager
    def resource():
        events.append("open")
        try:
            yield
        finally:
            events.append("close")

    def observe(state):
        assert state.run_called is True
        assert events == ["open"]
        state.update_callback()
        state.draw_callback()

    with (
        pytest.raises(ObservationFinished),
        headless_pyxel(on_run=observe) as state,
        resource(),
    ):
        pyxel.run(lambda: events.append("update"), lambda: events.append("draw"))
        events.append("after run")
    assert events == ["open", "update", "draw", "close"]
    assert state.quit_requested is False


def test_on_run_does_not_overwrite_callbacks_on_recursive_calls():
    import pyxel

    update = lambda: None
    draw = lambda: None

    def observe(state):
        with pytest.raises(RuntimeError, match="recursive or repeated"):
            pyxel.run(lambda: None, lambda: None)
        assert state.update_callback is update
        assert state.draw_callback is draw

    with pytest.raises(ObservationFinished), headless_pyxel(on_run=observe):
        pyxel.run(update, draw)


def test_on_run_rejects_a_second_call_after_observation_was_caught():
    import pyxel

    calls = []
    with headless_pyxel(on_run=lambda state: calls.append(state)) as state:
        with pytest.raises(ObservationFinished):
            pyxel.run(lambda: None, lambda: None)
        with pytest.raises(RuntimeError, match="recursive or repeated"):
            pyxel.run(lambda: None, lambda: None)
    assert calls == [state]


def test_quit_sets_request_and_restores_original_function():
    import pyxel

    saved = pyxel.quit
    with pytest.raises(QuitRequested), headless_pyxel() as state:
        assert state.quit_requested is False
        pyxel.quit()
    assert state.quit_requested is True
    assert pyxel.quit is saved


def test_quit_during_on_run_preserves_state_and_restores_patches():
    import pyxel

    originals = pyxel.run, pyxel.init, pyxel.quit

    def observe(state):
        state.update_callback()
        pytest.fail("quit must unwind the active callback")

    with pytest.raises(QuitRequested), headless_pyxel(on_run=observe) as state:
        pyxel.run(pyxel.quit, lambda: None)
    assert state.run_called is True
    assert state.quit_requested is True
    assert (pyxel.run, pyxel.init, pyxel.quit) == originals


@pytest.mark.parametrize("execute", [False, True])
def test_quit_before_run_prevents_observation_started_by_cleanup(execute):
    import pyxel

    observed = []
    on_run = (lambda state: observed.append(state)) if execute else None
    with pytest.raises(QuitRequested), headless_pyxel(on_run=on_run) as state:
        try:
            pyxel.quit()
        finally:
            pyxel.run(lambda: None, lambda: None)
    assert observed == []
    assert state.quit_requested is True
    assert state.run_called is False
    assert state.update_callback is state.draw_callback is None


def test_control_flow_signals_are_not_ordinary_script_errors():
    assert not issubclass(ObservationFinished, Exception)
    assert not issubclass(QuitRequested, Exception)


def test_fps_override_makes_flip_near_instant():
    """flip() sleeps to maintain pyxel's internal fps. The patcher must override
    fps to a high value so harness runs are near-instant rather than real-time.
    Without the override, a 60-flip loop would take ~2s at fps=30.
    """
    import time

    import pyxel

    with headless_pyxel():
        # User passes fps=30 explicitly — patcher must override anyway.
        pyxel.init(32, 32, fps=30)
        t0 = time.monotonic()
        for _ in range(60):
            pyxel.flip()
        elapsed = time.monotonic() - t0

    # Real-time at fps=30 = 2s; with override (fps=10000) ~0.1s. Allow generous
    # margin for slow CI machines but reject anything close to real-time.
    assert elapsed < 0.5, (
        f"60 flips took {elapsed:.3f}s — fps override appears not applied "
        f"(real-time would be ~2.0s)"
    )
