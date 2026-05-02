import pytest
from pyxel_mcp._harnesses._common.error_capture import (
    ToolError, ErrorPhase, make_error, make_validation_error
)


def test_phases_match_spec():
    expected = {"validation", "script_import", "asset_load", "build_assets", "game_loop", "snapshot"}
    assert {p.value for p in ErrorPhase} == expected


def test_make_validation_error_minimal():
    err = make_validation_error("bad input")
    assert err["phase"] == "validation"
    assert err["message"] == "bad input"
    assert err["path"] is None
    assert err["frame"] is None
    assert err["traceback"] is None


def test_make_validation_error_with_path():
    err = make_validation_error("bad input", path="/abs/script.py")
    assert err["path"] == "/abs/script.py"


def test_make_error_with_traceback():
    try:
        raise ValueError("kaboom")
    except ValueError:
        err = make_error(ErrorPhase.GAME_LOOP, "boom", frame=42, capture_traceback=True)
    assert err["phase"] == "game_loop"
    assert err["frame"] == 42
    assert "ValueError" in err["traceback"]


def test_make_error_unknown_phase_rejected():
    with pytest.raises(TypeError):
        make_error("not_a_phase_enum", "msg")  # passing a str instead of ErrorPhase


def test_make_error_capture_traceback_outside_except_returns_none():
    """capture_traceback=True outside an except block must NOT return 'NoneType: None\\n'."""
    err = make_error(ErrorPhase.GAME_LOOP, "no active exception", capture_traceback=True)
    assert err["traceback"] is None
