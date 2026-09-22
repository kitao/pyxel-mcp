"""state snapshot — read App or module attrs."""

from __future__ import annotations

import contextlib
import math
import re
import types
from typing import Any

_INDEX_RE = re.compile(r"^([A-Za-z_][\w]*)\[(\d+)\](.*)$")
_REPR_LIMIT = 200
_PLAIN_SCALARS = (int, float, str, bool, type(None))


class _DeferredRead(Exception):
    """Reading or representing a value could run user code."""


def _has_plain_type(value: object, allowed: tuple[type, ...]) -> bool:
    return any(type(value) is candidate for candidate in allowed)


def _class_attributes(cls: type) -> dict[str, Any]:
    """Read ordinary class storage without invoking metaclass hooks."""
    if type(cls) is not type:
        raise _DeferredRead
    attributes = {}
    for base in reversed(type.__getattribute__(cls, "__mro__")):
        namespace = type.__getattribute__(base, "__dict__")
        if any(type(key) is not str for key in namespace):
            raise _DeferredRead
        attributes.update(namespace)
    return attributes


def _storage(target: object) -> tuple[dict | None, dict]:
    if type(target) is type:
        return _class_attributes(target), _class_attributes(type)
    declared = _class_attributes(type(target))
    getter = declared.get("__getattribute__")
    if not any(
        getter is standard
        for standard in (object.__getattribute__, types.ModuleType.__getattribute__)
    ):
        raise _DeferredRead
    descriptor = declared.get("__dict__")
    if descriptor is None:
        return None, declared
    if not _has_plain_type(
        descriptor, (types.GetSetDescriptorType, types.MemberDescriptorType)
    ):
        raise _DeferredRead
    stored = descriptor.__get__(target, type(target))
    if type(stored) is not dict or any(type(key) is not str for key in stored):
        raise _DeferredRead
    return stored, declared


def _stored_attribute(target: object, name: str) -> object:
    stored, declared = _storage(target)
    if name == "__dict__" and stored is not None and type(target) is not type:
        return stored
    if name in declared:
        descriptor = declared[name]
        if type(descriptor) is types.MemberDescriptorType:
            return descriptor.__get__(target, type(target))
        protocol = _class_attributes(type(descriptor))
        if "__get__" in protocol and (
            "__set__" in protocol or "__delete__" in protocol
        ):
            raise _DeferredRead
    if stored is not None and name in stored:
        return stored[name]
    if name not in declared:
        if "__getattr__" in declared:
            raise _DeferredRead
        raise AttributeError(name)
    if "__get__" in protocol:
        raise _DeferredRead
    return descriptor


def _plain_python_data(value: object, seen: set[int]) -> bool:
    """Exclude subclass hooks and custom reprs, including inside containers."""
    if _has_plain_type(value, _PLAIN_SCALARS):
        return True
    if not _has_plain_type(value, (list, tuple, dict, set, frozenset)):
        return False
    if id(value) in seen:
        return True
    seen.add(id(value))
    items = (*value.keys(), *value.values()) if type(value) is dict else value
    return all(_plain_python_data(item, seen) for item in items)


def _serialize_static(value: object) -> Any:
    if _plain_python_data(value, set()):
        return _serialize_value(value)
    import numpy as np

    if type(value) is np.ndarray and value.dtype.kind in "biufU":
        return _serialize_array(value.tolist())
    if type(value) is np.float64:
        return _serialize_value(value)
    raise _DeferredRead


def _is_scalar(v: object) -> bool:
    return isinstance(v, (int, float, str, bool, type(None)))


def _serialize_value(v: object) -> Any:
    if _is_scalar(v):
        if isinstance(v, float) and not math.isfinite(v):
            return repr(float(v))
        return v
    if isinstance(v, list):
        if all(_is_scalar(x) for x in v):
            return [_serialize_value(x) for x in v]
        return _truncate_repr(v)
    if isinstance(v, dict):
        # JSON coerces non-string keys, which can merge distinct Python keys
        # such as 1 and "1". Preserve those dictionaries as a representation.
        if all(isinstance(k, str) and _is_scalar(val) for k, val in v.items()):
            return {k: _serialize_value(val) for k, val in v.items()}
        return _truncate_repr(v)
    try:
        import numpy as np

        if isinstance(v, np.ndarray):
            if v.dtype.kind not in "biufU":
                return _truncate_repr(v)
            return _serialize_array(v.tolist())
    except ImportError:
        pass
    return _truncate_repr(v)


def _serialize_array(v: object) -> Any:
    """Normalize numeric/string array leaves, including non-finite floats."""
    if isinstance(v, list):
        return [_serialize_array(item) for item in v]
    return _serialize_value(v)


def _truncate_repr(v: object) -> str:
    s = repr(v)
    return s if len(s) <= _REPR_LIMIT else s[:_REPR_LIMIT] + "<truncated>"


def _resolve_path(
    target: object, path: str, *, stored_only: bool = False
) -> tuple[object, bool]:
    """Walk a dotted/indexed path. Returns (value, found)."""
    cur: Any = target
    read = _stored_attribute if stored_only else getattr
    parts = path.split(".")
    for part in parts:
        m = _INDEX_RE.match(part)
        if m:
            name, idx_str, rest = m.group(1), m.group(2), m.group(3)
            try:
                cur = read(cur, name)
                if stored_only:
                    if not _has_plain_type(cur, (list, tuple, dict)):
                        raise _DeferredRead
                    if type(cur) is dict and not all(
                        _has_plain_type(key, _PLAIN_SCALARS) for key in cur
                    ):
                        raise _DeferredRead
                cur = cur[int(idx_str)]
            except (AttributeError, IndexError, KeyError, TypeError):
                return None, False
            if rest:
                # Recurse on rest (could be ".attr" or more indexes)
                if rest.startswith("."):
                    return _resolve_path(cur, rest[1:], stored_only=stored_only)
                return None, False  # malformed
        else:
            try:
                cur = read(cur, part)
            except AttributeError:
                return None, False
    return cur, True


def _top_level_scalars(target: object) -> dict[str, Any]:
    out: dict[str, Any] = {}
    if hasattr(target, "__dict__"):
        for k, v in vars(target).items():
            if not k.startswith("_") and _is_scalar(v):
                out[k] = _serialize_value(v)
    else:
        for k in dir(target):
            if k.startswith("_"):
                continue
            # Properties may raise on access; skip them like any other non-scalar.
            with contextlib.suppress(Exception):
                v = getattr(target, k)
                if _is_scalar(v):
                    out[k] = _serialize_value(v)
    return out


def capture(
    snapshot: dict[str, Any],
    *,
    app_instance: object | None,
    module: object | None,
    stored_only: bool = False,
) -> dict[str, Any]:
    """Read state, optionally retaining only data that needs no user-code evaluation."""
    warnings: list[str] = []
    target = app_instance if app_instance is not None else module
    if app_instance is None:
        warnings.append("no App class detected; reading module globals")

    attrs = snapshot.get("attrs")
    auto = attrs is None
    values = {}
    if auto and not stored_only:
        values = _top_level_scalars(target)
    else:
        if auto:
            try:
                stored, declared = _storage(target)
                attrs = [
                    name
                    for name in (stored if stored is not None else declared)
                    if not name.startswith("_")
                ]
            except _DeferredRead:
                attrs = []
                warnings.append(
                    "top-level attrs omitted after quit: reading them requires dynamic attribute access"
                )
        for path in attrs:
            try:
                v, found = _resolve_path(target, path, stored_only=stored_only)
                if found:
                    if auto:
                        import numpy as np

                        if (
                            not _has_plain_type(v, _PLAIN_SCALARS)
                            and type(v) is not np.float64
                        ):
                            continue
                    values[path] = (
                        _serialize_static(v) if stored_only else _serialize_value(v)
                    )
            except _DeferredRead:
                warnings.append(
                    f"attr '{path}' omitted after quit: its completed-frame value requires dynamic evaluation"
                )
                continue
            if not found:
                msg = f"attr '{path}' not found"
                # Specific hints for the two mistakes a fresh agent
                # tends to make (surfaced by e2e validation):
                if path.startswith("self."):
                    msg += (
                        " — note: state.attrs paths are evaluated against "
                        "the App instance directly, so do not include "
                        "the 'self.' prefix (use 'player.x', not "
                        "'self.player.x')"
                    )
                elif "(" in path or ")" in path:
                    msg += (
                        " — note: state.attrs paths do not support "
                        "function calls; expose a derived value as a "
                        "plain attribute (e.g. set self.n_hazards = "
                        "len(self.hazards) in update, then read "
                        "'n_hazards')"
                    )
                warnings.append(msg)
                continue

    return {
        "frame": snapshot["frame"],
        "kind": "state",
        "values": values,
        "warnings": warnings,
    }
