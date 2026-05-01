"""Tests for layout_harness decomposed analysis functions.

These functions operate on synthetic pixel grids and do not require
a running Pyxel instance.
"""

import sys
import os
import types
import importlib
from unittest.mock import MagicMock


def _import_layout_harness():
    """Import layout_harness with all pyxel/headless dependencies stubbed."""
    # Stub pyxel if not already a real module
    if "pyxel" not in sys.modules or not hasattr(sys.modules["pyxel"], "init"):
        pyxel_stub = types.ModuleType("pyxel")
        pyxel_stub.init = MagicMock()
        pyxel_stub.run = MagicMock()
        pyxel_stub.show = MagicMock()
        pyxel_stub.flip = MagicMock()
        pyxel_stub.quit = MagicMock()
        pyxel_stub.screenshot = MagicMock()
        pyxel_stub.pget = MagicMock(return_value=0)
        pyxel_stub.width = 16
        pyxel_stub.height = 16
        sys.modules["pyxel"] = pyxel_stub

    # Stub _common.headless to avoid real patching
    headless_stub = types.ModuleType("pyxel_mcp._common.headless")
    headless_stub.setup_harness = MagicMock()
    headless_stub.patch_game_loop = MagicMock()
    headless_stub.run_script = MagicMock()
    headless_stub.noop_game_loop = MagicMock()

    # Ensure src is in path
    src = os.path.join(os.path.dirname(__file__), "..", "src")
    if src not in sys.path:
        sys.path.insert(0, src)

    orig_argv = sys.argv[:]
    orig_headless = sys.modules.get("pyxel_mcp._common.headless")

    sys.argv = ["layout_harness", "dummy_script.py", "1"]
    sys.modules["pyxel_mcp._common.headless"] = headless_stub

    # Force fresh import
    if "pyxel_mcp.layout_harness" in sys.modules:
        del sys.modules["pyxel_mcp.layout_harness"]

    try:
        import pyxel_mcp.layout_harness as lh
    finally:
        sys.argv = orig_argv
        if orig_headless is not None:
            sys.modules["pyxel_mcp._common.headless"] = orig_headless
        else:
            sys.modules.pop("pyxel_mcp._common.headless", None)

    return lh


_lh = _import_layout_harness()

find_bg_color = _lh.find_bg_color
content_bbox = _lh.content_bbox
calc_balance = _lh.calc_balance
calc_margins = _lh.calc_margins
detect_text = _lh.detect_text
merge_text_spans = _lh.merge_text_spans
dedup_text_by_y = _lh.dedup_text_by_y
analyze_text_alignment = _lh.analyze_text_alignment
estimate_font_height = _lh.estimate_font_height
check_grid_alignment = _lh.check_grid_alignment


# --- find_bg_color ---

def test_find_bg_color_most_frequent():
    pixels = [[1, 1, 1], [1, 7, 1], [1, 1, 1]]
    assert find_bg_color(pixels) == 1


def test_find_bg_color_single_row():
    pixels = [[0, 0, 3, 0]]
    assert find_bg_color(pixels) == 0


def test_find_bg_color_tie_returns_one():
    # When equal counts, max() returns some valid color index
    pixels = [[0, 7]]
    result = find_bg_color(pixels)
    assert result in (0, 7)


# --- content_bbox ---

def test_content_bbox_with_content():
    pixels = [[0, 0, 0], [0, 7, 0], [0, 0, 0]]
    bbox = content_bbox(pixels, bg=0)
    assert bbox == {"x": 1, "y": 1, "w": 1, "h": 1}


def test_content_bbox_empty():
    pixels = [[0, 0], [0, 0]]
    assert content_bbox(pixels, bg=0) is None


def test_content_bbox_full_screen():
    pixels = [[7, 7], [7, 7]]
    bbox = content_bbox(pixels, bg=0)
    assert bbox == {"x": 0, "y": 0, "w": 2, "h": 2}


def test_content_bbox_top_row_only():
    pixels = [[3, 3, 3], [0, 0, 0], [0, 0, 0]]
    bbox = content_bbox(pixels, bg=0)
    assert bbox == {"x": 0, "y": 0, "w": 3, "h": 1}


def test_content_bbox_single_pixel():
    pixels = [[0, 0, 0], [0, 0, 5], [0, 0, 0]]
    bbox = content_bbox(pixels, bg=0)
    assert bbox == {"x": 2, "y": 1, "w": 1, "h": 1}


# --- calc_margins ---

def test_calc_margins_basic():
    bbox = {"x": 10, "y": 5, "w": 20, "h": 30}
    margins = calc_margins(bbox, 100, 80)
    assert margins["left"] == 10
    assert margins["right"] == 70
    assert margins["top"] == 5
    assert margins["bottom"] == 45


def test_calc_margins_centered():
    # Content of 10x10 centered in 30x30
    bbox = {"x": 10, "y": 10, "w": 10, "h": 10}
    margins = calc_margins(bbox, 30, 30)
    assert margins["left"] == margins["right"] == 10
    assert margins["top"] == margins["bottom"] == 10


def test_calc_margins_no_margin():
    bbox = {"x": 0, "y": 0, "w": 20, "h": 10}
    margins = calc_margins(bbox, 20, 10)
    assert margins["left"] == 0
    assert margins["right"] == 0
    assert margins["top"] == 0
    assert margins["bottom"] == 0


# --- calc_balance ---

def test_calc_balance_symmetric():
    # 4x4, content split evenly: columns 1 and 2 (mid=2)
    pixels = [
        [0, 7, 7, 0],
        [0, 7, 7, 0],
        [0, 7, 7, 0],
        [0, 7, 7, 0],
    ]
    result = calc_balance(pixels, bg=0)
    # col1 → x=1 < 2 → left; col2 → x=2 >= 2 → right
    assert result["fg_pixels"]["total"] == 8
    assert result["fg_pixels"]["left"] == result["fg_pixels"]["right"]
    assert result["h_balance"] == 1.0


def test_calc_balance_empty():
    pixels = [[0, 0], [0, 0]]
    result = calc_balance(pixels, bg=0)
    assert result["fg_pixels"]["total"] == 0
    assert result["h_balance"] == 0.0
    assert result["center_of_mass"] is None


def test_calc_balance_quadrants():
    # Single pixel in top-left quadrant (x<1, y<1 for 2x2)
    pixels = [[7, 0], [0, 0]]
    result = calc_balance(pixels, bg=0)
    assert result["quadrants"]["tl"] == 1
    assert result["quadrants"]["tr"] == 0
    assert result["quadrants"]["bl"] == 0
    assert result["quadrants"]["br"] == 0


def test_calc_balance_center_of_mass():
    # Single pixel at (2, 1) in 4x4
    pixels = [[0, 0, 0, 0], [0, 0, 7, 0], [0, 0, 0, 0], [0, 0, 0, 0]]
    result = calc_balance(pixels, bg=0)
    assert result["center_of_mass"] == {"x": 2.0, "y": 1.0}


# --- merge_text_spans ---

def test_merge_text_spans_adjacent():
    spans = [
        {"x": 0, "y": 10, "w": 5, "h": 6, "color": 7, "center_x": 2.5},
        {"x": 6, "y": 10, "w": 5, "h": 6, "color": 7, "center_x": 8.5},
    ]
    merged = merge_text_spans(spans)
    assert len(merged) == 1
    assert merged[0]["x"] == 0
    assert merged[0]["w"] == 11


def test_merge_text_spans_different_color():
    spans = [
        {"x": 0, "y": 10, "w": 5, "h": 6, "color": 7, "center_x": 2.5},
        {"x": 6, "y": 10, "w": 5, "h": 6, "color": 8, "center_x": 8.5},
    ]
    merged = merge_text_spans(spans)
    assert len(merged) == 2


def test_merge_text_spans_far_apart():
    spans = [
        {"x": 0, "y": 10, "w": 5, "h": 6, "color": 7, "center_x": 2.5},
        {"x": 100, "y": 10, "w": 5, "h": 6, "color": 7, "center_x": 102.5},
    ]
    merged = merge_text_spans(spans)
    assert len(merged) == 2


# --- dedup_text_by_y ---

def test_dedup_text_by_y_keeps_widest():
    spans = [
        {"x": 5, "y": 10, "w": 20, "h": 6, "color": 7, "center_x": 15.0},
        {"x": 5, "y": 10, "w": 30, "h": 6, "color": 7, "center_x": 20.0},
    ]
    result = dedup_text_by_y(spans)
    assert len(result) == 1
    assert result[0]["w"] == 30


def test_dedup_text_by_y_different_rows():
    spans = [
        {"x": 5, "y": 10, "w": 20, "h": 6, "color": 7, "center_x": 15.0},
        {"x": 5, "y": 20, "w": 30, "h": 6, "color": 7, "center_x": 20.0},
    ]
    result = dedup_text_by_y(spans)
    assert len(result) == 2
    assert result[0]["y"] == 10
    assert result[1]["y"] == 20


# --- analyze_text_alignment ---

def test_analyze_text_alignment_centered():
    # A span that is perfectly centered on a 100px screen
    text_lines = [{"x": 40, "y": 10, "w": 20, "h": 6, "color": 7, "center_x": 50.0}]
    result = analyze_text_alignment(text_lines, screen_w=100)
    assert len(result) == 1
    assert result[0]["offset_from_center"] == 0.0


def test_analyze_text_alignment_offset():
    text_lines = [{"x": 10, "y": 20, "w": 10, "h": 6, "color": 7, "center_x": 15.0}]
    result = analyze_text_alignment(text_lines, screen_w=100)
    assert result[0]["offset_from_center"] == -35.0  # 15 - 50


def test_analyze_text_alignment_empty():
    result = analyze_text_alignment([], screen_w=100)
    assert result == []


# --- estimate_font_height ---

def test_estimate_font_height_default():
    """Empty grid (all background) returns default of 6."""
    pixels = [[0] * 16 for _ in range(16)]
    assert estimate_font_height(pixels, bg=0) == 6


def test_estimate_font_height_empty_pixels():
    """Empty pixel list returns default of 6."""
    assert estimate_font_height([], bg=0) == 6


def test_estimate_font_height_detects_span():
    """Grid with an 8-row content band should estimate height ~8."""
    # Build a 20x20 grid: rows 4-11 have some non-bg pixels (sparse enough)
    pixels = [[0] * 20 for _ in range(20)]
    for y in range(4, 12):
        # Set a few pixels per row — bg_in_row should be >= 50%
        pixels[y][5] = 7
        pixels[y][6] = 7
        pixels[y][8] = 7
    result = estimate_font_height(pixels, bg=0)
    # Should return 8 (the height of the span)
    assert result == 8


# --- check_grid_alignment ---

def test_check_grid_alignment_8px():
    """Content at 8px-aligned position and size returns high 8px score."""
    bbox = {"x": 8, "y": 16, "w": 16, "h": 24}
    result = check_grid_alignment(bbox, [])
    assert result is not None
    assert result[8]["score"] == 4
    assert result[8]["x"] is True
    assert result[8]["y"] is True
    assert result[8]["w"] is True
    assert result[8]["h"] is True


def test_check_grid_alignment_16px():
    """Content at 16px-aligned position and size returns high 16px score."""
    bbox = {"x": 16, "y": 32, "w": 48, "h": 64}
    result = check_grid_alignment(bbox, [])
    assert result is not None
    assert result[16]["score"] == 4
    assert result[8]["score"] == 4  # 16px-aligned is also 8px-aligned


def test_check_grid_alignment_none():
    """No bbox returns None."""
    result = check_grid_alignment(None, [])
    assert result is None


def test_check_grid_alignment_partial():
    """Partially aligned content returns intermediate scores."""
    bbox = {"x": 8, "y": 5, "w": 16, "h": 10}  # x,w aligned to 8; y,h not
    result = check_grid_alignment(bbox, [])
    assert result is not None
    assert result[8]["score"] == 2
    assert result[8]["x"] is True
    assert result[8]["y"] is False
    assert result[8]["w"] is True
    assert result[8]["h"] is False
