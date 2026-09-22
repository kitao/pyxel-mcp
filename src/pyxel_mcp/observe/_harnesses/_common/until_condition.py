"""Until-condition evaluation for run(until=...)."""

from __future__ import annotations

from typing import Any

# Minimal builtins whitelist. The observed script is trusted local code;
# this is not a sandbox, just a guard against accidental side effects
# (open, __import__) inside a condition expression.
_SAFE_BUILTINS: dict[str, Any] = {
    "abs": abs,
    "len": len,
    "min": min,
    "max": max,
    "int": int,
    "float": float,
    "round": round,
    "bool": bool,
}


class UntilError(Exception):
    """An until expression failed for a reason other than a not-yet-defined
    name or attribute."""


class _AttrNamespace(dict):
    """Resolve target attributes in both outer and nested expression scopes."""

    def __init__(self, target: object):
        super().__init__(__builtins__=_SAFE_BUILTINS)
        self._target = target

    def __missing__(self, name: str) -> Any:
        try:
            return getattr(self._target, name)
        except AttributeError:
            raise KeyError(name)


class UntilCondition:
    """Compiled `until` expression evaluated against the running app.

    NameError/AttributeError mean "not yet satisfied" (the attribute may be
    created in a later scene); the first such miss is reported once via
    `pending_warning`. Any other exception raises UntilError.
    """

    def __init__(self, expr: str):
        self.expr = expr
        self._code = compile(expr, "<until>", "eval")  # SyntaxError propagates
        self.pending_warning: str | None = None
        self._warned = False

    def evaluate(self, target: object) -> bool:
        try:
            # Comprehensions, generators and lambdas look up free names in
            # globals, not eval's locals. Share one lazy namespace so those
            # expressions observe the same attributes as a simple comparison.
            namespace = _AttrNamespace(target)
            return bool(eval(self._code, namespace, namespace))
        except (NameError, AttributeError) as e:
            if not self._warned:
                self._warned = True
                self.pending_warning = (
                    f"until expression {self.expr!r} references an undefined "
                    f"name or attribute ({type(e).__name__}: {e}); treating as "
                    "not yet satisfied"
                )
            return False
        except Exception as e:
            raise UntilError(
                f"until expression {self.expr!r} raised {type(e).__name__}: {e}"
            ) from e
