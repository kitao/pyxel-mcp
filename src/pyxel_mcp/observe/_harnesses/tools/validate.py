"""validate(script) — static analysis on script source (spec §8.1)."""
from __future__ import annotations
import ast
from pathlib import Path
from typing import Any

from pyxel_mcp.observe._harnesses._common.error_capture import make_validation_error
from pyxel_mcp.observe._harnesses._common.script_loader import resolve_script_path


_SEVERITY_ORDER = {"error": 0, "warning": 1, "info": 2}

# Pixel-emitting pyxel APIs — any call to these renders pixels (spec §8.1 cls_missing)
_PIXEL_EMIT_APIS = frozenset(
    ["blt", "bltm", "pset", "line", "rect", "rectb", "circ", "circb", "tri", "trib", "text"]
)

# assets_in_update detector
_ASSET_CONTAINERS = frozenset(["images", "tilemaps"])
_ASSET_METHODS = frozenset(["set", "load"])

# iter_modify detector — list-mutating method names
_LIST_MUTATING = frozenset(["append", "remove", "pop", "insert", "clear", "extend"])

# degree_radian_mix detector — trig function names
_MATH_TRIG = frozenset(["sin", "cos", "tan", "asin", "acos", "atan", "atan2"])
_PYXEL_TRIG = frozenset(["sin", "cos"])


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


def _detect_syntax(source: str) -> tuple[list[dict[str, Any]], ast.AST | None]:
    """Parse source and return (issues, tree).

    Returns a single 'syntax' issue and None tree on parse failure;
    returns empty issues and the parsed tree on success.
    """
    try:
        tree = ast.parse(source)
        return [], tree
    except SyntaxError as e:
        return [_make_issue("error", e.lineno or 0, e.offset, "syntax", str(e))], None


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
    """pyxel.tilemaps[N].set(...) whose tile-data list references source-bank (0,0).

    Constrained to pyxel.tilemaps[...].set(...) calls to avoid false positives
    from unrelated .set() calls (e.g., pyxel.images[0].set()).
    Heuristic: flag if the data list contains a string with '0000' or '0102'.
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Must be <expr>.set(...)
        if not (isinstance(func, ast.Attribute) and func.attr == "set"):
            continue
        # The receiver must be pyxel.tilemaps[N] or tilemaps[N]
        receiver = func.value
        if not isinstance(receiver, ast.Subscript):
            continue
        subscript_value = receiver.value
        is_tilemaps = (
            (isinstance(subscript_value, ast.Name) and subscript_value.id == "tilemaps")
            or (
                isinstance(subscript_value, ast.Attribute)
                and subscript_value.attr == "tilemaps"
                and isinstance(subscript_value.value, ast.Name)
                and subscript_value.value.id == "pyxel"
            )
        )
        if not is_tilemaps:
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


def _detect_assets_in_update(tree: ast.AST) -> list[dict[str, Any]]:
    """pyxel.images[N].set/load or pyxel.tilemaps[N].set called inside update() or draw().

    Asset loading is expensive and should happen in __init__, not the game loop.
    Uses _walk_excluding_scopes to stay in the lexical body of the method.
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name not in ("update", "draw"):
            continue
        for child in _walk_excluding_scopes(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            # Pattern: <something>.set(...) or <something>.load(...)
            if not (isinstance(func, ast.Attribute) and func.attr in _ASSET_METHODS):
                continue
            # Receiver must be images[N] or tilemaps[N] (with or without `pyxel.` prefix)
            receiver = func.value
            if not isinstance(receiver, ast.Subscript):
                continue
            sub_val = receiver.value
            is_asset = (
                (isinstance(sub_val, ast.Name) and sub_val.id in _ASSET_CONTAINERS)
                or (
                    isinstance(sub_val, ast.Attribute)
                    and sub_val.attr in _ASSET_CONTAINERS
                    and isinstance(sub_val.value, ast.Name)
                    and sub_val.value.id == "pyxel"
                )
            )
            if is_asset:
                issues.append(_make_issue(
                    "warning", child.lineno, child.col_offset,
                    "anti_pattern.assets_in_update",
                    f"asset load/set inside {node.name}() runs every frame — move to __init__()",
                ))
    return issues


def _iter_node_key(node: ast.expr) -> str | None:
    """Return a stable string key for an iterable expression, or None if not trackable.

    Supports:
    - bare Name:             `lst`          → "lst"
    - attribute access:      `self.bullets` → "self.bullets"

    Calls (range/enumerate/etc.) return None so they are not tracked.
    """
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        return f"{node.value.id}.{node.attr}"
    return None


def _call_receiver_key(node: ast.Call) -> str | None:
    """Return the key for the object a Call is invoked on, matching _iter_node_key."""
    func = node.func
    if not isinstance(func, ast.Attribute):
        return None
    receiver = func.value
    if isinstance(receiver, ast.Name):
        return receiver.id
    if isinstance(receiver, ast.Attribute) and isinstance(receiver.value, ast.Name):
        return f"{receiver.value.id}.{receiver.attr}"
    return None


def _detect_iter_modify(tree: ast.AST) -> list[dict[str, Any]]:
    """List modified (append/remove/pop/insert/clear/extend) while being iterated.

    Detects `for x in lst:` / `for x in self.lst:` bodies that call
    lst.<mutating_method>(...) on the same object being iterated.

    Only fires when the iterable is a bare Name or a one-level attribute
    (e.g. self.bullets). Calls to range()/enumerate()/etc. return None from
    _iter_node_key and are not tracked.

    Heuristic: does not follow aliasing (a = lst; for x in a: lst.remove(x)).
    Uses _walk_excluding_scopes so nested for loops over the same list don't
    cause duplicate reports, and a nested def inside the loop body doesn't
    falsely fire (the nested def runs in its own scope, not during iteration).
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.For):
            continue
        list_key = _iter_node_key(node.iter)
        if list_key is None:
            continue
        for child in _walk_excluding_scopes(node):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in _LIST_MUTATING:
                continue
            receiver_key = _call_receiver_key(child)
            if receiver_key == list_key:
                issues.append(_make_issue(
                    "warning", child.lineno, child.col_offset,
                    "anti_pattern.iter_modify",
                    f"'{list_key}.{func.attr}()' called while iterating '{list_key}' — use a copy or collect indices",
                ))
    return issues


def _detect_btn_one_shot(tree: ast.AST) -> list[dict[str, Any]]:
    """pyxel.btn(K) inside an `if` that triggers a one-shot action.

    Heuristic (info severity): flag `if pyxel.btn(...):` blocks whose body
    contains pyxel.play() — a sound trigger that should fire only once per
    press. btn() re-fires every frame the key is held; btnp() fires once.

    This is intentionally conservative to minimise false positives. Only
    `pyxel.play(...)` inside the if-body is used as the signal; general
    btn()-guarded code is not flagged.
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        # Check if the test is pyxel.btn(...)
        test = node.test
        if not (
            isinstance(test, ast.Call)
            and isinstance(test.func, ast.Attribute)
            and isinstance(test.func.value, ast.Name)
            and test.func.value.id == "pyxel"
            and test.func.attr == "btn"
        ):
            continue
        # Check if any statement in the body calls pyxel.play(...)
        for stmt in ast.walk(ast.Module(body=node.body, type_ignores=[])):
            if not isinstance(stmt, ast.Call):
                continue
            func = stmt.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "pyxel"
                and func.attr == "play"
            ):
                issues.append(_make_issue(
                    "info", test.lineno, test.col_offset,
                    "anti_pattern.btn_one_shot",
                    "pyxel.btn() fires every frame the key is held — use btnp() for one-shot actions like sounds or state changes",
                ))
                break  # one issue per if-block
    return issues


def _detect_palette_animation(tree: ast.AST) -> list[dict[str, Any]]:
    """pyxel.colors[N] = X (or augmented-assignment) inside a For or While loop body.

    Palette mutation per frame inside a loop is a performance trap.
    Uses _walk_excluding_scopes inside the loop body to avoid false positives
    from nested function definitions. Handles AugAssign (`|=`, `^=`, etc.)
    consistently with _detect_update_in_draw.
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.For, ast.While)):
            continue
        for child in _walk_excluding_scopes(node):
            if isinstance(child, ast.Assign):
                targets = child.targets
            elif isinstance(child, ast.AugAssign):
                targets = [child.target]
            else:
                continue
            for target in targets:
                if not isinstance(target, ast.Subscript):
                    continue
                sub_val = target.value
                is_colors = (
                    (isinstance(sub_val, ast.Name) and sub_val.id == "colors")
                    or (
                        isinstance(sub_val, ast.Attribute)
                        and sub_val.attr == "colors"
                        and isinstance(sub_val.value, ast.Name)
                        and sub_val.value.id == "pyxel"
                    )
                )
                if is_colors:
                    issues.append(_make_issue(
                        "warning", child.lineno, child.col_offset,
                        "anti_pattern.palette_animation",
                        "pyxel.colors[N] = X inside a loop — palette mutation per frame is expensive; prefer pal() for per-draw remapping",
                    ))
    return issues


def _detect_cls_missing(tree: ast.AST) -> list[dict[str, Any]]:
    """draw() contains a pixel-emitting API call before any pyxel.cls() call.

    Traverses each `draw` method's body in order. Flags the method if a
    pixel-emitting call (blt, bltm, pset, line, rect, rectb, circ, circb,
    tri, trib, text) appears before the first cls() call.

    Permitted before cls(): assignments, conditional return, pal/dither calls,
    and any other non-pixel-emitting statements.

    Note: helper-method inlining (one-level deep) is not implemented in v0.9.3.
    Only direct pixel-emitting calls in the draw body are checked.
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef) or node.name != "draw":
            continue
        _check_draw_body(node, issues)
    return issues


def _check_draw_body(func_node: ast.FunctionDef, issues: list[dict[str, Any]]) -> None:
    """Scan draw() body statements in order; flag the first pixel-emitting call
    that appears before any cls() call.
    """
    for stmt in func_node.body:
        # Walk this single statement (excluding nested scopes) to find pyxel calls
        for child in _walk_or_single(stmt):
            if not isinstance(child, ast.Call):
                continue
            func = child.func
            if not (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and func.value.id == "pyxel"
            ):
                continue
            api = func.attr
            if api == "cls":
                # cls() found — everything from here is fine
                return
            if api in _PIXEL_EMIT_APIS:
                issues.append(_make_issue(
                    "warning", child.lineno, child.col_offset,
                    "anti_pattern.cls_missing",
                    f"pyxel.{api}() called before pyxel.cls() in draw() — screen will accumulate ghost trails",
                ))
                return  # report once per draw()


def _walk_or_single(node: ast.AST):
    """Yield node and all descendants, excluding nested scopes."""
    yield node
    if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        yield from _walk_excluding_scopes(node)


def _detect_ragged_image_set(tree: ast.AST) -> list[dict[str, Any]]:
    """pyxel.images[N].set(x, y, data) where `data` is a list of string
    constants whose lengths differ — Pyxel raises `Invalid sound note` /
    `byte index out of bounds` at runtime when reading mismatched rows.

    Catches the trap of a 32x32 sprite written with some 30-char rows
    (β-DK validation surfaced this).

    Heuristic: all-string elements must share the same length. A list with
    any non-string-constant element is skipped (can't statically check).
    """
    issues: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        # Must be <expr>.set(...)
        if not (isinstance(func, ast.Attribute) and func.attr == "set"):
            continue
        # Receiver must be pyxel.images[N] or images[N]
        receiver = func.value
        if not isinstance(receiver, ast.Subscript):
            continue
        sub_val = receiver.value
        is_images = (
            (isinstance(sub_val, ast.Name) and sub_val.id == "images")
            or (
                isinstance(sub_val, ast.Attribute)
                and sub_val.attr == "images"
                and isinstance(sub_val.value, ast.Name)
                and sub_val.value.id == "pyxel"
            )
        )
        if not is_images:
            continue
        # The 3rd positional arg should be a list of string constants
        if len(node.args) < 3:
            continue
        data_arg = node.args[2]
        if not isinstance(data_arg, ast.List):
            continue
        # Collect string-constant lengths; bail if any element is not a string
        # constant (variable reference, computed expression, etc.).
        lengths: list[int] = []
        for elt in data_arg.elts:
            if not (isinstance(elt, ast.Constant) and isinstance(elt.value, str)):
                lengths = []
                break
            lengths.append(len(elt.value))
        if not lengths:
            continue
        unique = set(lengths)
        if len(unique) > 1:
            issues.append(_make_issue(
                "warning", node.lineno, node.col_offset,
                "anti_pattern.ragged_image_set",
                f"pyxel.images[N].set() data has rows of differing lengths "
                f"{sorted(unique)} — Pyxel raises 'byte index out of bounds' "
                f"at runtime; pad every row to the same hex-string width",
            ))
    return issues


def _detect_degree_radian_mix(tree: ast.AST) -> list[dict[str, Any]]:
    """math.sin/cos and pyxel.sin/cos used in the same module.

    math trig functions take radians; pyxel trig functions take degrees.
    Mixing them is a silent numerical bug. Both sets of call sites are flagged
    when co-occurrence is detected.
    """
    math_calls: list[ast.Call] = []
    pyxel_calls: list[ast.Call] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute):
            continue
        if (
            isinstance(func.value, ast.Name)
            and func.value.id == "math"
            and func.attr in _MATH_TRIG
        ):
            math_calls.append(node)
        elif (
            isinstance(func.value, ast.Name)
            and func.value.id == "pyxel"
            and func.attr in _PYXEL_TRIG
        ):
            pyxel_calls.append(node)

    if not (math_calls and pyxel_calls):
        return []

    issues: list[dict[str, Any]] = []
    for call in math_calls:
        issues.append(_make_issue(
            "warning", call.lineno, call.col_offset,
            "anti_pattern.degree_radian_mix",
            f"math.{call.func.attr}() takes radians but pyxel trig takes degrees — mixing causes silent numerical errors",
        ))
    for call in pyxel_calls:
        issues.append(_make_issue(
            "warning", call.lineno, call.col_offset,
            "anti_pattern.degree_radian_mix",
            f"pyxel.{call.func.attr}() takes degrees but math trig takes radians — mixing causes silent numerical errors",
        ))
    return issues


# Registry of all AST-based detectors; run() iterates this list.
_DETECTORS = [
    _detect_missing_colkey,
    _detect_update_in_draw,
    _detect_tilemap_zero_zero,
    _detect_assets_in_update,
    _detect_iter_modify,
    _detect_btn_one_shot,
    _detect_palette_animation,
    _detect_cls_missing,
    _detect_degree_radian_mix,
    _detect_ragged_image_set,
]


def run(payload: dict[str, Any]) -> dict[str, Any]:
    """Static analysis on script source — entry point called by dispatch loop.

    Result includes `ok: bool` — True iff zero `error`-severity issues AND
    `len(errors) == 0`. Warning / info severity issues do not affect `ok`.
    """
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

    syntax_issues, tree = _detect_syntax(source)
    if syntax_issues:
        # Skip AST-based detectors when syntax is broken.
        issues.extend(syntax_issues)
    else:
        for detector in _DETECTORS:
            issues.extend(detector(tree))

    # Dedup by (line, col, category): nested AST traversals (e.g., a `for` loop
    # whose body contains another `for` over the same list) can have a detector
    # report the same site multiple times. Same-site different-category is kept
    # because two distinct anti-patterns at one location are both signal.
    seen: set[tuple[int, int | None, str]] = set()
    deduped: list[dict[str, Any]] = []
    for issue in issues:
        key = (issue["line"], issue["col"], issue["category"])
        if key in seen:
            continue
        seen.add(key)
        deduped.append(issue)
    issues = deduped

    issues.sort(key=lambda i: (i["line"], _SEVERITY_ORDER.get(i["severity"], 99)))
    has_error_issues = any(i["severity"] == "error" for i in issues)
    return {"ok": not has_error_issues, "issues": issues, "errors": []}
