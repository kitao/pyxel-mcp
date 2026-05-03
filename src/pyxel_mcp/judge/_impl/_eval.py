"""Sandboxed predicate evaluator shared by judge_milestone / judge_genre.

A predicate is a single boolean Python expression — comparisons, boolean
ops, attribute / subscript access, arithmetic. No calls, no statements,
no imports, no dunder access, no exponentiation, no integer literals
larger than `_MAX_INT_LITERAL`. Names resolve against a flat dict where
dotted keys (`player.x`) are auto-promoted into nested SimpleNamespace
attributes.

Hardening rationale:
- `ast.Pow` is removed because `9 ** 9 ** 9` is a one-line CPU bomb
  with no legitimate milestone use. If a predicate genuinely needs a
  squared distance, write `dx*dx + dy*dy` — that's bounded by the
  multiplier guard.
- Integer constants are capped at `_MAX_INT_LITERAL` so neither a
  raw 10-digit literal nor `[1] * 10**6` can exhaust memory.
- Dunder attribute access (`x.__class__`) is rejected at AST-walk
  time. With Call already forbidden, this is defence in depth — but
  the next time a feature loosens the Call ban, the door is closed.
- Predicate result must be exactly `bool`. A bare `x.bit_length`
  silently evaluating to a method object would otherwise be truthy
  and produce a spurious pass.
"""
from __future__ import annotations
import ast
import types
from typing import Any

# Largest integer literal the predicate may contain. Milestone predicates
# evaluate frame counters / scores / lives — none of which exceed 6 figures
# in any plausible Pyxel game. Anything bigger is either a typo or a DoS.
_MAX_INT_LITERAL = 1_000_000

# AST nodes the evaluator accepts. `ast.Pow` is deliberately absent — see
# module docstring. Any other node aborts at parse time.
_ALLOWED_NODES: set[type[ast.AST]] = {
    ast.Expression,
    ast.BoolOp, ast.UnaryOp, ast.BinOp, ast.Compare, ast.IfExp,
    ast.Name, ast.Load, ast.Constant, ast.Attribute, ast.Subscript,
    ast.List, ast.Tuple, ast.Set,
    ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod,
    ast.USub, ast.UAdd, ast.Invert,
}


def _check_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_NODES:
            raise ValueError(
                f"unsupported predicate construct: {type(node).__name__}"
            )
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise ValueError(
                f"dunder attribute access not allowed: {node.attr}"
            )
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            if abs(node.value) > _MAX_INT_LITERAL:
                raise ValueError(
                    f"integer literal {node.value} exceeds limit "
                    f"{_MAX_INT_LITERAL}"
                )


def _to_namespace(d: Any) -> Any:
    if isinstance(d, dict):
        return types.SimpleNamespace(**{k: _to_namespace(v) for k, v in d.items()})
    return d


def build_globals(flat: dict[str, Any]) -> dict[str, Any]:
    """Build an eval-globals dict from a flat key→value mapping.

    Keys with dots (`player.x`) are expanded into nested SimpleNamespaces so
    `player.x` resolves naturally. Plain keys (`scene`) become top-level names.
    """
    nested: dict[str, dict] = {}
    plain: dict[str, Any] = {}
    for key, value in flat.items():
        if "." in key:
            parts = key.split(".")
            d = nested.setdefault(parts[0], {})
            for p in parts[1:-1]:
                d = d.setdefault(p, {})
            d[parts[-1]] = value
        else:
            plain[key] = value

    g: dict[str, Any] = {"__builtins__": {}}
    for top, sub in nested.items():
        g[top] = _to_namespace(sub)
    g.update(plain)
    return g


def eval_predicate(expr: str, names: dict[str, Any]) -> bool:
    """Evaluate `expr` against `names` and return the boolean result.

    Raises ValueError on parse errors, sandbox violations (disallowed
    AST node, dunder access, oversized integer literal), or non-bool
    results. Lets NameError / AttributeError / TypeError / KeyError
    propagate from evaluation so callers can route them to spec failures.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"syntax error: {e.msg}") from e
    _check_ast(tree)
    code = compile(tree, "<predicate>", "eval")
    g = build_globals(names)
    result = eval(code, g, {})  # noqa: S307 — sandbox enforced via _check_ast
    if not isinstance(result, bool):
        raise ValueError(
            f"predicate must return bool, got {type(result).__name__}; "
            "wrap it in a comparison or boolean op"
        )
    return result
