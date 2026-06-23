"""Validation helpers for caller-requested artifact output paths."""
from __future__ import annotations

from pathlib import Path
from typing import Any


def absolute_path_error(value: Any, field: str) -> str | None:
    """Return a validation message when `value` is not an absolute path."""
    if not isinstance(value, str) or not value:
        return f"`{field}` must be a non-empty str"
    if not Path(value).is_absolute():
        return f"`{field}` must be an absolute path"
    return None
