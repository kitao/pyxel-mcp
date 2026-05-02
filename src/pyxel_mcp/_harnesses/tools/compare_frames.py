"""compare_frames tool (spec §9.1).

Pixel-wise diff between two PNG files. Returns size_match, identical,
changed_pixels, ratio, and bounding region of differing pixels.
"""
from __future__ import annotations
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, UnidentifiedImageError

from pyxel_mcp._harnesses._common.error_capture import make_validation_error


def _error_result(error: dict) -> dict:
    return {
        "identical": False,
        "size_match": False,
        "size_a": None,
        "size_b": None,
        "changed_pixels": None,
        "total_pixels": None,
        "ratio": None,
        "region": None,
        "warnings": [],
        "errors": [error],
    }


def run(payload: dict[str, Any]) -> dict[str, Any]:
    a = payload.get("frame_a")
    b = payload.get("frame_b")

    if not isinstance(a, str):
        return _error_result(make_validation_error("missing or non-str `frame_a`"))
    if not isinstance(b, str):
        return _error_result(make_validation_error("missing or non-str `frame_b`"))

    if not Path(a).is_file():
        return _error_result(make_validation_error(f"missing input: {a}", path=a))
    if not Path(b).is_file():
        return _error_result(make_validation_error(f"missing input: {b}", path=b))

    # Open and normalize to RGB
    try:
        img_a = Image.open(a).convert("RGB")
    except (UnidentifiedImageError, OSError) as e:
        return _error_result(make_validation_error(f"cannot decode image: {a}: {e}", path=a))

    try:
        img_b = Image.open(b).convert("RGB")
    except (UnidentifiedImageError, OSError) as e:
        return _error_result(make_validation_error(f"cannot decode image: {b}: {e}", path=b))

    size_a = list(img_a.size)  # [width, height]
    size_b = list(img_b.size)

    if img_a.size != img_b.size:
        return {
            "identical": False,
            "size_match": False,
            "size_a": size_a,
            "size_b": size_b,
            "changed_pixels": None,
            "total_pixels": None,
            "ratio": None,
            "region": None,
            "warnings": ["size mismatch; pixel comparison skipped"],
            "errors": [],
        }

    # Pixel diff via numpy
    arr_a = np.asarray(img_a)  # shape (h, w, 3)
    arr_b = np.asarray(img_b)
    mask = (arr_a != arr_b).any(axis=2)  # 2D bool mask

    h, w = mask.shape
    total_pixels = h * w
    changed_pixels = int(mask.sum())

    if changed_pixels == 0:
        return {
            "identical": True,
            "size_match": True,
            "size_a": size_a,
            "size_b": size_b,
            "changed_pixels": 0,
            "total_pixels": total_pixels,
            "ratio": 0.0,
            "region": None,
            "warnings": [],
            "errors": [],
        }

    # Bounding box of differing pixels
    ys, xs = np.where(mask)
    x_min, x_max = int(xs.min()), int(xs.max())
    y_min, y_max = int(ys.min()), int(ys.max())
    region = {
        "x": x_min,
        "y": y_min,
        "w": x_max - x_min + 1,
        "h": y_max - y_min + 1,
    }

    return {
        "identical": False,
        "size_match": True,
        "size_a": size_a,
        "size_b": size_b,
        "changed_pixels": changed_pixels,
        "total_pixels": total_pixels,
        "ratio": changed_pixels / total_pixels,
        "region": region,
        "warnings": [],
        "errors": [],
    }
