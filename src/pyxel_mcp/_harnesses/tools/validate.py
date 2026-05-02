"""validate(script) — static analysis on script source (spec §8.1)."""
from __future__ import annotations
import ast
from pathlib import Path
from typing import Any

from pyxel_mcp._harnesses._common.error_capture import make_validation_error
from pyxel_mcp._harnesses._common.script_loader import resolve_script_path


_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}


def _make_issue(
    severity: str, line: int, col: int | None, category: str, message: str
) -> dict[str, Any]:
    return {"severity": severity, "line": line, "col": col, "category": category, "message": message}


def _walk_excluding_scopes(node: ast.AST):
    """ast.walk variant that does NOT descend into nested scope-introducing nodes
    (ClassDef, FunctionDef, AsyncFunctionDef, Lambda). Use when an analysis
    targets statements lexically inside `node` itself, not inside nested
    methods/classes/closures that happen to share the source span.
    """
    for child in ast.iter_child_nodes(node):
        yield child
        if not isinstance(child, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            yield from _walk_excluding_scopes(child)


def _detect_syntax(source: str) -> list[dict[str, Any]]:
    """Return a single 'syntax' issue if ast.parse fails; else empty list."""
    try:
        ast.parse(source)
        return []
    except SyntaxError as e:
        return [_make_issue("error", e.lineno or 0, e.offset, "syntax", str(e))]


def _detect_missing_colkey(tree: ast.AST) -> list[dict[str, Any]]:
    """pyxel.blt called without `colkey=` — sprite background will be opaque."""
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            if func.value.id == "pyxel" and func.attr == "blt":
                # colkey is the 8th positional arg or a keyword arg
                if len(node.args) < 8 and not any(kw.arg == "colkey" for kw in node.keywords):
                    issues.append(_make_issue(
                        "warning", node.lineno, node.col_offset,
                        "anti_pattern.missing_colkey",
                        "pyxel.blt called without `colkey=` — sprite background will not be transparent",
                    ))
    return issues


def _detect_update_in_draw(tree: ast.AST) -> list[dict[str, Any]]:
    """Assignment or augmented-assignment to self.X inside any method named `draw`.

    Nested ClassDef / FunctionDef bodies are excluded — `self` in a nested scope
    refers to a different object, so flagging those would be a false positive.
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "draw":
            continue
        for child in _walk_excluding_scopes(node):
            if isinstance(child, ast.Assign):
                targets = child.targets
            elif isinstance(child, ast.AugAssign):
                targets = [child.target]
            else:
                continue
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "self"
                ):
                    issues.append(_make_issue(
                        "warning", child.lineno, child.col_offset,
                        "anti_pattern.update_in_draw",
                        f"draw() mutates self.{target.attr} — move to update()",
                    ))
    return issues


def _detect_tilemap_zero_zero(tree: ast.AST) -> list[dict[str, Any]]:
    """tilemaps[N].set(...) whose tile-data list contains a reference to source-bank (0, 0).

    Heuristic: look for `.set(x, y, [...])` calls whose tile-data list contains
    a string element matching '0000' or '0102'.  The '0102' pattern matches the
    canonical fixture; '0000' catches blank-tile floods.  This is intentionally
    crude — a more exact detector is deferred to Task 2.2.
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and func.attr == "set"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.List):
                for elt in arg.elts:
                    if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                        if "0000" in elt.value or "0102" in elt.value:
                            issues.append(_make_issue(
                                "warning", node.lineno, node.col_offset,
                                "anti_pattern.tilemap_zero_zero",
                                "tilemap data references source-bank (0,0) — placing visible content there floods the entire tilemap",
                            ))
                            break
    return issues


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Entry point called by main.py dispatch loop."""
    script = payload.get("script")
    if not isinstance(script, str):
        return {
            "ok": False,
            "issues": [],
            "errors": [make_validation_error("missing or non-str script field")],
        }

    try:
        path = resolve_script_path(script)
    except FileNotFoundError as e:
        return {
            "ok": False,
            "issues": [],
            "errors": [make_validation_error(str(e), path=script)],
        }

    try:
        source = path.read_text()
    except (UnicodeDecodeError, OSError) as e:
        return {
            "ok": False,
            "issues": [],
            "errors": [make_validation_error(f"cannot read script: {e}", path=script)],
        }
    issues: list[dict[str, Any]] = []

    syntax_issues = _detect_syntax(source)
    if syntax_issues:
        # Skip AST-based detectors when syntax is broken.
        issues.extend(syntax_issues)
    else:
        tree = ast.parse(source)
        issues.extend(_detect_missing_colkey(tree))
        issues.extend(_detect_update_in_draw(tree))
        issues.extend(_detect_tilemap_zero_zero(tree))

    issues.sort(key=lambda i: (i["line"], _SEVERITY_ORDER.get(i["severity"], 99)))
    has_errors = any(i["severity"] == "error" for i in issues)
    return {"ok": not has_errors, "issues": issues, "errors": []}
