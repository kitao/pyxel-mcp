"""Sandboxed predicate evaluator shared by judge_milestone / judge_genre.

A predicate is a single boolean Python expression — comparisons, boolean
ops, attribute / subscript access, arithmetic. No calls, no statements, no
imports. Names resolve against a flat dict where dotted keys (`player.x`)
are auto-promoted into nested SimpleNamespace attributes.
"""
from __future__ import annotations
import ast
import types
from typing import Any

# AST nodes the evaluator accepts. Any other node aborts at parse time.
_ALLOWED_NODES: set[type[ast.AST]] = {
    ast.Expression,
    ast.BoolOp, ast.UnaryOp, ast.BinOp, ast.Compare, ast.IfExp,
    ast.Name, ast.Load, ast.Constant, ast.Attribute, ast.Subscript,
    ast.List, ast.Tuple, ast.Set,
    ast.And, ast.Or, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
    ast.In, ast.NotIn, ast.Is, ast.IsNot,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.USub, ast.UAdd, ast.Invert,
}


def _check_ast(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if type(node) not in _ALLOWED_NODES:
            raise ValueError(f"unsupported predicate construct: {type(node).__name__}")


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
    """Evaluate `expr` against `names`.

    Raises ValueError on parse errors or sandbox violations. Lets NameError /
    AttributeError / TypeError / KeyError propagate from evaluation so callers
    can route them to spec failures.
    """
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ValueError(f"syntax error: {e.msg}") from e
    _check_ast(tree)
    code = compile(tree, "<predicate>", "eval")
    g = build_globals(names)
    return bool(eval(code, g, {}))  # noqa: S307 — sandbox enforced via _check_ast
