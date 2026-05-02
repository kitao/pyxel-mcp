"""state snapshot — read App or module attrs (spec §6.4.3)."""
from __future__ import annotations
import re
from typing import Any

_INDEX_RE = re.compile(r"^([A-Za-z_][\w]*)\[(\d+)\](.*)$")
_REPR_LIMIT = 200


def _is_scalar(v: object) -> bool:
    return isinstance(v, (int, float, str, bool, type(None)))


def _serialize_value(v: object) -> Any:
    if _is_scalar(v):
        return v
    if isinstance(v, list):
        if all(_is_scalar(x) for x in v):
            return list(v)
        return _truncate_repr(v)
    if isinstance(v, dict):
        if all(_is_scalar(k) and _is_scalar(val) for k, val in v.items()):
            return dict(v)
        return _truncate_repr(v)
    try:
        import numpy as np
        if isinstance(v, np.ndarray):
            return v.tolist()
    except ImportError:
        pass
    return _truncate_repr(v)


def _truncate_repr(v: object) -> str:
    s = repr(v)
    return s if len(s) <= _REPR_LIMIT else s[:_REPR_LIMIT] + "<truncated>"


def _resolve_path(target: object, path: str) -> tuple[object, bool]:
    """Walk a dotted/indexed path. Returns (value, found)."""
    cur: Any = target
    parts = path.split(".")
    for part in parts:
        m = _INDEX_RE.match(part)
        if m:
            name, idx_str, rest = m.group(1), m.group(2), m.group(3)
            try:
                cur = getattr(cur, name)
                cur = cur[int(idx_str)]
            except (AttributeError, IndexError, KeyError, TypeError):
                return None, False
            if rest:
                # Recurse on rest (could be ".attr" or more indexes)
                if rest.startswith("."):
                    return _resolve_path(cur, rest[1:])
                return None, False  # malformed
        else:
            try:
                cur = getattr(cur, part)
            except AttributeError:
                return None, False
    return cur, True


def _top_level_scalars(target: object) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if hasattr(target, "__dict__"):
        for k, v in vars(target).items():
            if not k.startswith("_") and _is_scalar(v):
                out[k] = v
    else:
        for k in dir(target):
            if k.startswith("_"):
                continue
            try:
                v = getattr(target, k)
            except Exception:
                continue
            if _is_scalar(v):
                out[k] = v
    return out


def capture(
    snapshot: dict[str, Any],
    *,
    app_instance: object | None,
    module: object | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    target = app_instance if app_instance is not None else module
    if app_instance is None:
        warnings.append("no App class detected; reading module globals")

    attrs = snapshot.get("attrs", None)
    if attrs is None:
        values = _top_level_scalars(target)
    elif attrs == []:
        values = {}
    else:
        values = {}
        for path in attrs:
            v, found = _resolve_path(target, path)
            if not found:
                warnings.append(f"attr '{path}' not found")
                continue
            values[path] = _serialize_value(v)

    return {
        "frame": snapshot["frame"],
        "kind": "state",
        "values": values,
        "warnings": warnings,
    }
