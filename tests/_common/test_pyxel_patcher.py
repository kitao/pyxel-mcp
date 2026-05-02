import os
import pytest
from pyxel_mcp._harnesses._common.pyxel_patcher import (
    PreLoopState, headless_pyxel, RunNotCalledError
)


def test_sets_sdl_videodriver():
    with headless_pyxel() as state:
        assert os.environ.get("SDL_VIDEODRIVER") == "dummy"


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
        def update(self): pass
        def draw(self): pass

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
