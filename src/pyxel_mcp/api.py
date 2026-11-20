"""Read declarations and documentation from the installed Pyxel type stubs."""

from __future__ import annotations

import ast
from functools import cache
from importlib.util import find_spec
from pathlib import Path

from pyxel_mcp.observe._harnesses._common.error_capture import make_validation_error


def stub_path(module: str) -> Path:
    spec = find_spec("pyxel")
    if spec is None or spec.origin is None:
        raise FileNotFoundError("Pyxel is not installed")
    root = Path(spec.origin).parent
    if module == "pyxel.cube":
        root /= "cube"
    return root / "__init__.pyi"


@cache
def _index() -> dict[str, list[str]]:
    symbols: dict[str, list[str]] = {}

    def collect(body: list[ast.stmt], parent: str) -> None:
        for i, node in enumerate(body):
            doc = None
            if isinstance(node, ast.ClassDef):
                symbols[f"{parent}.{node.name}"] = [f"class {node.name}"]
                collect(node.body, f"{parent}.{node.name}")
                continue
            if isinstance(node, ast.FunctionDef):
                name = node.name
                decorators = "".join(
                    f"@{ast.unparse(d)}\n" for d in node.decorator_list
                )
                declaration = f"{decorators}def {name}({ast.unparse(node.args)})"
                if node.returns:
                    declaration += f" -> {ast.unparse(node.returns)}"
                doc = ast.get_docstring(node)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                name = node.target.id
                declaration = ast.unparse(node)
                following = body[i + 1] if i + 1 < len(body) else None
                if (
                    isinstance(following, ast.Expr)
                    and isinstance(following.value, ast.Constant)
                    and isinstance(following.value.value, str)
                ):
                    doc = following.value.value
            else:
                continue
            entry = declaration if not doc else f"{declaration}\n\n{doc}"
            symbols.setdefault(f"{parent}.{name}", []).append(entry)

    for module in ("pyxel", "pyxel.cube"):
        tree = ast.parse(stub_path(module).read_text(encoding="utf-8"))
        collect(tree.body, module)
    return symbols


def lookup(name: str) -> dict:
    try:
        symbols = _index()
    except (OSError, SyntaxError, UnicodeError) as exc:
        return {
            "ok": False,
            "errors": [make_validation_error(f"Cannot read Pyxel API: {exc}")],
        }

    query = name.strip()
    if not query or any(not part.isidentifier() for part in query.split(".")):
        return {
            "ok": False,
            "errors": [
                make_validation_error(
                    "Use a Python name such as blt or cube.Vec3.lerp."
                )
            ],
        }

    for key in (query, f"pyxel.{query}", f"pyxel.cube.{query}"):
        if key in symbols:
            children = [
                s.removeprefix(key + ".") for s in symbols if s.startswith(key + ".")
            ]
            return {
                "ok": True,
                "errors": [],
                "name": key,
                "match_count": 1,
                "matches": [key],
                "declarations": symbols[key] + symbols.get(key + ".__init__", []),
                "members": [child for child in children if not child.startswith("_")],
            }

    needle = query.casefold()
    matches = [
        s
        for s in symbols
        if needle in s.casefold() and not s.split(".")[-1].startswith("_")
    ]
    return {
        "ok": True,
        "errors": [],
        "matches": matches[:30],
        "match_count": len(matches),
    }
