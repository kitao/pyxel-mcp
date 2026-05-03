"""Tests for `run_to_preloop` context manager (Task 3b-3)."""
from pyxel_mcp.observe._harnesses._common.preloop import PreloopFailed, run_to_preloop
from tests.conftest import SCRIPTS


def _empty(error: dict) -> dict:
    return {"ok": False, "errors": [error]}


def test_missing_script_raises_preloop_failed():
    """Non-string script triggers a validation-shaped PreloopFailed."""
    try:
        with run_to_preloop({}, empty_factory=_empty):
            pass
    except PreloopFailed as f:
        assert f.result["ok"] is False
        assert f.result["errors"][0]["phase"] == "validation"
    else:
        raise AssertionError("PreloopFailed should have been raised")


def test_missing_file_raises_preloop_failed():
    """File-not-found triggers a validation-shaped PreloopFailed with path."""
    try:
        with run_to_preloop({"script": "/no/such/file.py"}, empty_factory=_empty):
            pass
    except PreloopFailed as f:
        assert f.result["errors"][0]["phase"] == "validation"
        assert f.result["errors"][0]["path"] == "/no/such/file.py"
    else:
        raise AssertionError("PreloopFailed should have been raised")


def test_no_pyxel_run_raises_preloop_failed():
    """A script that imports but never calls pyxel.run() trips
    require_run_called() — PreloopFailed surfaces script_import phase.
    """
    try:
        with run_to_preloop(
            {"script": str(SCRIPTS / "no_pyxel_run.py")},
            empty_factory=_empty,
        ):
            pass
    except PreloopFailed as f:
        assert f.result["errors"][0]["phase"] == "script_import"
    else:
        raise AssertionError("PreloopFailed should have been raised")


def test_yields_state_on_success():
    """Body sees the headless_pyxel state object when the script loads."""
    seen = {}
    with run_to_preloop(
        {"script": str(SCRIPTS / "minimal.py")},
        empty_factory=_empty,
    ) as state:
        seen["state"] = state
    # state.app_instance is set when the script's class instantiates pyxel.run.
    assert "state" in seen
