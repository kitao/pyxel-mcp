"""Adversarial tests for the sandboxed predicate evaluator.

These tests pin sandbox guarantees that judge_milestone / judge_genre
rely on — predicates from PLAN.md or agent-supplied contracts must not
be able to hang the server, escape via dunders, or coerce a non-bool
result into a spurious pass.
"""
from __future__ import annotations

import pytest

from pyxel_mcp.judge._impl._eval import eval_predicate


# ---------- happy path: still works after hardening ----------------------

def test_simple_comparison_passes():
    assert eval_predicate("x > 10", {"x": 50}) is True


def test_compound_boolean_passes():
    assert eval_predicate("x > 10 and y < 5", {"x": 50, "y": 1}) is True


def test_in_operator_on_log_passes():
    assert eval_predicate("'WIN' in log", {"log": "frame 600 WIN"}) is True


def test_dotted_attribute_access_passes():
    ns = {"player.x": 30, "player.y": 100}
    assert eval_predicate("player.x > 10 and player.y < 200", ns) is True


def test_subscript_access_passes():
    assert eval_predicate("scores[0] > 100", {"scores": [150, 200]}) is True


def test_arithmetic_within_limits_passes():
    assert eval_predicate("(dx + dy) > 100", {"dx": 60, "dy": 50}) is True


# ---------- DoS: exponentiation ------------------------------------------

def test_pow_operator_is_rejected():
    """`9 ** 9 ** 9` is a one-line CPU bomb — Pow is now off the allow-list."""
    with pytest.raises(ValueError, match="Pow|unsupported"):
        eval_predicate("9 ** 9 ** 9 > 0", {})


def test_modest_pow_also_rejected():
    """No exception for `x ** 2`: still off the allow-list, no carve-outs."""
    with pytest.raises(ValueError, match="Pow|unsupported"):
        eval_predicate("x ** 2 > 4", {"x": 3})


# ---------- DoS: huge integer literals -----------------------------------

def test_oversize_integer_literal_rejected():
    with pytest.raises(ValueError, match="integer literal"):
        eval_predicate("x > 10000000000", {"x": 5})


def test_integer_literal_exactly_at_limit_passes():
    """1_000_000 is the documented ceiling (inclusive)."""
    assert eval_predicate("x < 1000000", {"x": 5}) is True


def test_oversize_via_unary_minus_also_rejected():
    """`-99999999999` should still be caught — abs() check covers signed."""
    with pytest.raises(ValueError, match="integer literal"):
        eval_predicate("x > -99999999999", {"x": 5})


def test_list_repeat_with_oversize_literal_rejected():
    """`[1] * 10000000` would allocate 80MB at minimum; the literal limit
    catches it before evaluation. (No Call here — `len()` would be
    rejected for a different reason and mask the literal-limit check.)"""
    with pytest.raises(ValueError, match="integer literal"):
        eval_predicate("[1] * 10000000 == [1]", {})


# ---------- sandbox escape: dunder attribute access ----------------------

def test_dunder_class_access_rejected():
    with pytest.raises(ValueError, match="dunder"):
        eval_predicate("s.__class__", {"s": "x"})


def test_dunder_subclasses_chain_rejected():
    with pytest.raises(ValueError, match="dunder"):
        eval_predicate(
            "s.__class__.__mro__[-1].__subclasses__",
            {"s": "x"},
        )


def test_dunder_globals_rejected():
    with pytest.raises(ValueError, match="dunder"):
        eval_predicate("f.__globals__", {"f": lambda: None})


# ---------- non-bool result -----------------------------------------------

def test_method_reference_no_call_rejected():
    """`x.bit_length` (no parens) was silently truthy before — a typo where
    the agent forgot the `()`. Now reject as non-bool."""
    with pytest.raises(ValueError, match="must return bool"):
        eval_predicate("x.bit_length", {"x": 5})


def test_string_method_reference_rejected():
    with pytest.raises(ValueError, match="must return bool"):
        eval_predicate("s.upper", {"s": "win"})


def test_arithmetic_non_bool_rejected():
    """Even useful-looking arithmetic must be wrapped in a comparison."""
    with pytest.raises(ValueError, match="must return bool"):
        eval_predicate("x + y", {"x": 1, "y": 2})


# ---------- structural rejections (regression: previously always rejected) ----

def test_function_call_rejected():
    with pytest.raises(ValueError, match="Call|unsupported"):
        eval_predicate("len(x) > 0", {"x": "abc"})


def test_lambda_rejected():
    with pytest.raises(ValueError, match="Lambda|unsupported"):
        eval_predicate("(lambda: True)()", {})


def test_import_rejected_via_syntax():
    with pytest.raises(ValueError):
        eval_predicate("__import__('os')", {})


def test_assignment_rejected():
    with pytest.raises(ValueError):
        eval_predicate("x := 5", {})
