"""Script validation for Pyxel programs."""

import ast
import re

PYXEL_ANTIPATTERNS = [
    (
        r"pyxel\.run\s*\(",
        "draw",
        "pyxel.run() called inside draw(). Move it to __init__.",
    ),
    (
        r"pyxel\.init\s*\(",
        "update",
        "pyxel.init() called inside update(). Move it to __init__.",
    ),
    (
        r"pyxel\.init\s*\(",
        "draw",
        "pyxel.init() called inside draw(). Move it to __init__.",
    ),
    (
        r"math\.sin\b|math\.cos\b",
        None,
        "Using math.sin/cos (radians). Pyxel's pyxel.sin/cos use degrees.",
    ),
    (
        r"random\.randint\b",
        None,
        "Using random.randint. Prefer pyxel.rndi(a, b) for Pyxel games.",
    ),
    (
        r"for\s+\w+\s+in\s+(\w+)\s*:.*\n\s+\1\.remove\(",
        None,
        "Mutating list while iterating. Use: for e in list(items): items.remove(e)",
    ),
]


def validate_source(source, filename="script.py"):
    """Validate Pyxel script source code. Returns report string."""
    issues = []

    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        return f"Syntax error at line {e.lineno}: {e.msg}"

    # Collect function/method bodies for context-aware checks
    method_bodies = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno or start
            body_lines = source.split("\n")[start - 1:end]
            method_bodies[node.name] = "\n".join(body_lines)

    # Anti-pattern checks
    for pattern, context, message in PYXEL_ANTIPATTERNS:
        text = method_bodies.get(context, "") if context else source
        if re.search(pattern, text, re.DOTALL):
            issues.append(message)

    # Check for missing pyxel import
    if not re.search(r"import\s+pyxel|from\s+pyxel", source):
        issues.append("No 'import pyxel' found.")

    # Check for missing pyxel.init
    if not re.search(r"pyxel\.init\s*\(", source):
        issues.append("No pyxel.init() call found.")

    # Check for game loop
    has_run = bool(re.search(r"pyxel\.run\s*\(", source))
    has_show = bool(re.search(r"pyxel\.show\s*\(", source))
    has_flip = bool(re.search(r"pyxel\.flip\s*\(", source))
    if not (has_run or has_show or has_flip):
        issues.append("No pyxel.run(), show(), or flip() call found.")

    # Check for cls in draw
    if "draw" in method_bodies:
        if not re.search(r"pyxel\.cls\s*\(|cls\s*\(", method_bodies["draw"]):
            issues.append("draw() may be missing pyxel.cls(). Screen won't clear.")

    # Basic stats
    n_classes = sum(1 for n in ast.walk(tree) if isinstance(n, ast.ClassDef))
    n_functions = sum(1 for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    n_lines = len(source.split("\n"))

    report = f"Script: {filename}"
    report += f"  ({n_lines} lines, {n_classes} classes, {n_functions} functions)"

    if issues:
        report += f"\n\nWarnings ({len(issues)}):"
        for issue in issues:
            report += f"\n  - {issue}"
    else:
        report += "\n\nNo issues found."

    return report
