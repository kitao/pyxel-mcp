"""Multi-frame range-string parser (spec §6.6)."""
from __future__ import annotations
import re


class RangeError(ValueError):
    """Raised when a frames range/list is malformed or out of bounds."""


_RANGE_RE = re.compile(r"^(\d+):(\d+)(?::(\d+))?$")


def resolve_frames(
    frames: list[int] | str,
    *,
    total_frames: int,
) -> tuple[list[int], bool]:
    """Resolve a frames input to a sorted, deduplicated list of frame indices.

    Returns (resolved_frames, was_normalized) where `was_normalized` is True if
    the explicit list required sort/dedup. Range strings and "all" always
    return False — they are inherently ordered and unique.
    """
    if isinstance(frames, list):
        if not frames:
            raise RangeError("empty frames list")
        if not all(isinstance(f, int) for f in frames):
            raise RangeError(f"non-int element in frames list: {frames}")
        for f in frames:
            if f < 0 or f >= total_frames:
                raise RangeError(f"frame {f} out of bounds [0, {total_frames})")
        sorted_unique = sorted(set(frames))
        return sorted_unique, sorted_unique != frames

    if isinstance(frames, str):
        if frames == "all":
            return list(range(total_frames)), False
        m = _RANGE_RE.match(frames)
        if not m:
            raise RangeError(f"malformed range string: {frames!r}")
        start = int(m.group(1))
        end = int(m.group(2))
        step = int(m.group(3)) if m.group(3) is not None else 1
        if step < 1:
            raise RangeError(f"step must be >= 1, got {step}")
        if start >= end:
            raise RangeError(f"start ({start}) must be < end ({end})")
        if start < 0:
            raise RangeError(f"start must be >= 0, got {start}")
        if end > total_frames:
            raise RangeError(f"end ({end}) must be <= total_frames ({total_frames})")
        return list(range(start, end, step)), False

    raise RangeError(f"frames must be list[int] or str, got {type(frames).__name__}")
