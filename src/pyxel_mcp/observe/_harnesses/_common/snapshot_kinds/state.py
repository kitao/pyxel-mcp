"""state snapshot — read App or module attrs."""

from __future__ import annotations

import contextlib
import inspect
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


def _class_storage(cls: type) -> list[Any]:
    if type(cls) is not type:
        raise _DeferredRead
    storage = []
    for base in type.__getattribute__(cls, "__mro__"):
        if type(base) is not type:
            raise _DeferredRead
        namespace = type.__getattribute__(base, "__dict__")
        if any(type(key) is not str for key in namespace):
            raise _DeferredRead
        storage.append(namespace)
    return storage


def _getattr_static(target: object, name: str, default: Any = None) -> Any:
    """Guard inspect's dictionary lookups against metaclass and key hooks."""
    cls = type(target)
    storage = _class_storage(cls)
    if any(base is type for base in type.__getattribute__(cls, "__mro__")):
        _class_storage(target)
    else:
        for namespace in storage:
            if "__dict__" not in namespace:
                continue
            descriptor = namespace["__dict__"]
            if not _has_plain_type(
                descriptor, (types.GetSetDescriptorType, types.MemberDescriptorType)
            ):
                raise _DeferredRead
            instance_vars = descriptor.__get__(target, cls)
            if type(instance_vars) is not dict or any(
                type(key) is not str for key in instance_vars
            ):
                raise _DeferredRead
            break
    return inspect.getattr_static(target, name, default)


def _static_attribute(target: object, name: str) -> object:
    getter = _getattr_static(type(target), "__getattribute__")
    if not any(
        getter is standard
        for standard in (
            object.__getattribute__,
            type.__getattribute__,
            types.ModuleType.__getattribute__,
        )
    ):
        raise _DeferredRead
    missing = object()
    value = _getattr_static(target, name, missing)
    if value is missing:
        if _getattr_static(target, "__getattr__") is not None:
            raise _DeferredRead
        raise AttributeError(name)
    if type(value) is types.MemberDescriptorType:
        return value.__get__(target, type(target))
    # The standard instance/module dictionary is safe to inspect. Other
    # getset descriptors, including extension attributes, remain deferred.
    if (
        name == "__dict__"
        and type(value) is types.GetSetDescriptorType
        and value.__name__ == "__dict__"
    ):
        value = value.__get__(target, type(target))
        if type(value) is not dict:
            raise _DeferredRead
        return value
    if _getattr_static(type(value), "__get__") is not None:
        raise _DeferredRead
    return value


def _static_path(target: object, path: str) -> object:
    cur = target
    for part in path.split("."):
        match = _INDEX_RE.match(part)
        if match:
            name, index, rest = match.groups()
            if rest:
                raise AttributeError(path)
            cur = _static_attribute(cur, name)
            if not _has_plain_type(cur, (list, tuple, dict)):
                raise _DeferredRead
            if type(cur) is dict and not all(
                _has_plain_type(k, _PLAIN_SCALARS) for k in cur
            ):
                raise _DeferredRead
            cur = cur[int(index)]
        else:
            cur = _static_attribute(cur, part)
    return cur


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


def capture_static(
    snapshot: dict[str, Any],
    *,
    app_instance: object | None,
    module: object | None,
) -> dict[str, Any]:
    """Keep completed-frame data without evaluating getters or custom reprs.

    Only used when a later partial frame quits. Normal end snapshots use the
    ordinary capture function once at the actual end of observation.
    """
    target = app_instance if app_instance is not None else module
    warnings = (
        []
        if app_instance is not None
        else ["no App class detected; reading module globals"]
    )
    values = {}
    attrs = snapshot.get("attrs")
    if attrs is None:
        try:
            try:
                namespace = _static_attribute(target, "__dict__")
                names = [
                    name
                    for name in namespace
                    if type(name) is str and not name.startswith("_")
                ]
            except AttributeError:
                # Slots have no instance dictionary. Inspect class storage
                # without calling the script's __dir__ implementation.
                names = {
                    name
                    for cls in type.__getattribute__(type(target), "__mro__")
                    for name in type.__getattribute__(cls, "__dict__")
                    if type(name) is str and not name.startswith("_")
                }
        except _DeferredRead:
            names = []
            warnings.append(
                "top-level attrs omitted after quit: reading them requires "
                "dynamic attribute access"
            )
        for name in names:
            try:
                value = _static_attribute(target, name)
                import numpy as np

                if _has_plain_type(value, _PLAIN_SCALARS) or type(value) is np.float64:
                    values[name] = _serialize_static(value)
            except (_DeferredRead, AttributeError):
                warnings.append(
                    f"attr '{name}' omitted after quit: it requires dynamic access"
                )
    else:
        for path in attrs:
            try:
                values[path] = _serialize_static(_static_path(target, path))
            except _DeferredRead:
                warnings.append(
                    f"attr '{path}' omitted after quit: its completed-frame value "
                    "requires a getter, custom indexing, or custom representation"
                )
            except (AttributeError, IndexError, KeyError, TypeError):
                warnings.append(f"attr '{path}' not found")
    return {
        "frame": snapshot["frame"],
        "kind": "state",
        "values": values,
        "warnings": warnings,
    }


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
            values[path] = _serialize_value(v)

    return {
        "frame": snapshot["frame"],
        "kind": "state",
        "values": values,
        "warnings": warnings,
    }
