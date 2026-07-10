"""Unit tests for UntilCondition (no Pyxel dependency)."""
import pytest

from pyxel_mcp.observe._harnesses._common.until_condition import (
    UntilCondition, UntilError,
)


class _Obj:
    pass


def make_target(**attrs):
    t = _Obj()
    for k, v in attrs.items():
        setattr(t, k, v)
    return t


def test_simple_comparison_true():
    assert UntilCondition("score >= 1").evaluate(make_target(score=1)) is True


def test_simple_comparison_false():
    assert UntilCondition("score >= 1").evaluate(make_target(score=0)) is False


def test_dotted_attribute_access():
    player = make_target(y=120)
    assert UntilCondition("player.y > 100").evaluate(make_target(player=player)) is True


def test_safe_builtins_available():
    assert UntilCondition("len(items) == 2").evaluate(make_target(items=[1, 2])) is True


def test_missing_name_is_false_with_single_warning():
    cond = UntilCondition("ghost > 0")
    t = make_target()
    assert cond.evaluate(t) is False
    assert cond.pending_warning is not None
    cond.pending_warning = None
    assert cond.evaluate(t) is False
    assert cond.pending_warning is None  # warned only once


def test_missing_nested_attribute_is_false():
    cond = UntilCondition("player.y > 0")
    assert cond.evaluate(make_target(player=make_target())) is False


def test_syntax_error_raises_at_construction():
    with pytest.raises(SyntaxError):
        UntilCondition("score >=")


def test_runtime_error_raises_until_error():
    with pytest.raises(UntilError):
        UntilCondition("len(5) > 0").evaluate(make_target())


def test_forbidden_builtin_is_treated_as_missing_name():
    # open() is not whitelisted: NameError -> "not yet satisfied"
    assert UntilCondition("open('/etc/hosts')").evaluate(make_target()) is False
