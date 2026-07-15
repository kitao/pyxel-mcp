"""Tests for direct palette observations."""

import pyxel
import pytest

from pyxel_mcp.observe._harnesses._common.analyzers.palette import analyze_palette


@pytest.fixture(autouse=True)
def _restore_state():
    try:
        original = list(pyxel.colors)
        pyxel.images[0].cls(0)
    except Exception:
        pyxel.init(8, 8)
        original = list(pyxel.colors)
    yield
    while len(pyxel.colors) > len(original):
        pyxel.colors.pop()
    pyxel.images[0].cls(0)


def test_default_palette_reports_color_values():
    result = analyze_palette()

    assert result["palette_size"] == 16
    assert result["extended_palette"] is False
    assert all(value.startswith("#") and len(value) == 7 for value in result["colors"].values())


def test_extended_palette_is_reported_without_interpretation():
    pyxel.colors.append(0xFF8800)

    result = analyze_palette()

    assert result["extended_palette"] is True
    assert result["palette_size"] == 17


def test_used_indices_are_sorted_and_include_zero():
    pyxel.images[0].pset(0, 0, 11)
    pyxel.images[0].pset(1, 0, 3)

    result = analyze_palette()

    assert result["used_indices"] == [0, 3, 11]


def test_palette_scan_completes_under_500ms():
    import time

    started = time.monotonic()
    result = analyze_palette()

    assert time.monotonic() - started < 0.5
    assert result["errors"] == []
